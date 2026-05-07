"""Critical RAG Judge Agent for blind A/B validation packets.

This is a deterministic, audit-friendly implementation of the agent spec in:
  agents/critical-rag-judge/SPEC.md

It intentionally judges packet answers before revealing raw_context/wiki identity.
After scoring, it may use blind_key.json only for aggregate reporting.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_./:-]*")
CITATION_RE = re.compile(r"\^\[raw/articles/([^\]]+)\]")
REF_RE = re.compile(r"<ref:([^>]+)>")

JUNK_ARTIFACTS = {
    "coffee", "bicycle", "bicycles", "weather", "irrelevant", "mention", "acros",
    "text", "string", "const", "let", "var", "case", "false", "true", "nil", "self",
}

CRITICAL_PRODUCT_TERMS = {
    "payment", "payments", "credit", "credits", "subscription", "subscriptions", "receipt",
    "auth", "token", "security", "storage", "rls", "policy", "privacy", "delete", "paypal",
    "storekit", "supabase", "apple", "testflight", "appstore", "migration", "generation",
}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def term_forms(term: str) -> set[str]:
    base = norm(term)
    forms = {base}
    if base.endswith("s") and len(base) > 3:
        forms.add(base[:-1])
    else:
        forms.add(base + "s")
    forms.add(base.replace(" ", ""))
    forms.add(base.replace(" ", "-"))
    forms.add(base.replace(" ", "_"))
    return {f for f in forms if f}


def has_term(answer: str, term: str) -> bool:
    low = answer.lower()
    normalized = " " + norm(answer) + " "
    for form in term_forms(term):
        if not form:
            continue
        if form in low:
            return True
        if f" {form} " in normalized:
            return True
    return False


def clamp_score(value: float) -> int:
    return max(1, min(5, int(round(value))))


def parse_packet(path: Path) -> tuple[str, str, str]:
    text = path.read_text(errors="ignore")
    packet_id = path.stem
    m = re.search(r"^# Blind Review Packet:\s*(.+)$", text, re.M)
    if m:
        packet_id = m.group(1).strip()
    split_a = re.split(r"^## Answer A\s*$", text, flags=re.M)
    if len(split_a) < 2:
        raise ValueError(f"Could not find Answer A in {path}")
    rest = split_a[1]
    split_b = re.split(r"^## Answer B\s*$", rest, flags=re.M)
    if len(split_b) < 2:
        raise ValueError(f"Could not find Answer B in {path}")
    answer_a = split_b[0].strip()
    answer_b = split_b[1].strip()
    return packet_id, answer_a, answer_b


def extract_question_from_report(report_path: Path) -> str:
    if not report_path.exists():
        return ""
    text = report_path.read_text(errors="ignore")
    for pat in [r"^Question:\s*(.+)$", r"^## Question\s*\n(.+)$"]:
        m = re.search(pat, text, re.M)
        if m:
            return m.group(1).strip()
    return ""


def source_slug(source: str) -> str:
    slug = source.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug


@dataclass
class ArmScore:
    correctness: int
    grounding: int
    source_coverage: int
    completeness: int
    synthesis: int
    product_benefit: int
    communication: int
    grounded_quality_total: float
    overall_total: float
    evidence_notes: list[str]
    failure_flags: list[str]
    raw_metrics: dict[str, Any]


def score_answer(answer: str, case: dict[str, Any], packet_root: Path | None = None) -> ArmScore:
    expected_terms = case.get("expected_terms", []) or []
    expected_sources = case.get("expected_sources", []) or []
    low = answer.lower()
    lines = [ln for ln in answer.splitlines() if ln.strip()]
    words = WORD_RE.findall(answer)
    word_count = len(words)

    term_hits = [t for t in expected_terms if has_term(answer, t)]
    source_hits = []
    for s in expected_sources:
        s_low = s.lower()
        if s_low in low or source_slug(s) in low:
            source_hits.append(s)

    citations = CITATION_RE.findall(answer)
    unique_citations = sorted(set(citations))
    refs = REF_RE.findall(answer)
    unique_refs = sorted(set(refs))

    has_source_map = "## source map" in low
    has_relevant_pages = "## relevant wiki pages" in low
    has_artifact_inventory = "artifact inventory" in low
    has_query_artifact = "queries/" in low
    has_synthesis_section = "## synthesis" in low or "synthesis" in low
    has_cross_source = bool(re.search(r"\bacross\s+\d+\s+sources\b|cross-source|recurring pattern|therefore", low))
    has_answer_intro = "answer based on supplied project sources" in low

    code_line_ratio = 0.0
    if lines:
        code_markers = sum(
            1
            for ln in lines
            if re.search(r"^\s*(let|var|func|case|if|for|return|const|await|try|private|struct|class|enum|//|\{|\}|\)|\])\b", ln)
            or ln.strip().startswith(("|", "- ["))
        )
        code_line_ratio = code_markers / max(len(lines), 1)

    expected_term_ratio = len(term_hits) / max(len(expected_terms), 1)
    expected_source_ratio = len(source_hits) / max(len(expected_sources), 1)
    citation_source_ratio = len(unique_citations) / max(len(expected_sources), 1)

    # Unsupported-overclaim risk proxy: critical product/security/payment terms without citations or source hits.
    critical_mentions = {t for t in CRITICAL_PRODUCT_TERMS if re.search(rf"\b{re.escape(t)}\b", low)}
    unsupported_risk = 0
    if critical_mentions and not citations and expected_sources:
        unsupported_risk += 1
    if word_count > 900 and len(term_hits) < max(2, len(expected_terms) // 3):
        unsupported_risk += 1

    junk_refs = sorted(set(unique_refs) & JUNK_ARTIFACTS)
    junk_artifacts = [r for r in junk_refs if r in low]

    correctness = clamp_score(1 + 4 * expected_term_ratio)
    grounding_base = 1 + 2.2 * min(1.0, citation_source_ratio) + 1.0 * expected_source_ratio
    if citations:
        grounding_base += 0.8
    grounding = clamp_score(grounding_base - unsupported_risk)
    source_coverage = clamp_score(1 + 4 * max(expected_source_ratio, min(1.0, citation_source_ratio)))
    completeness = clamp_score(1 + 2.4 * expected_term_ratio + 1.4 * expected_source_ratio)
    synthesis = clamp_score(1 + (1.7 if has_synthesis_section else 0) + (1.6 if has_cross_source else 0) + 0.8 * expected_source_ratio)

    artifact_points = sum([has_source_map, has_relevant_pages, has_artifact_inventory, has_query_artifact])
    product_benefit = clamp_score(1 + artifact_points * 0.85 + min(1.0, citation_source_ratio) * 0.8 + (0.4 if has_cross_source else 0))
    if junk_artifacts:
        product_benefit = max(1, product_benefit - 1)

    communication_base = 3.0
    if has_synthesis_section or has_answer_intro:
        communication_base += 0.7
    if word_count > 1400:
        communication_base -= 0.8
    if code_line_ratio > 0.55 and not has_synthesis_section:
        communication_base -= 1.0
    if has_source_map and has_synthesis_section:
        communication_base += 0.4
    communication = clamp_score(communication_base)

    flags: list[str] = []
    if expected_term_ratio < 0.55:
        flags.append("missed_expected_term")
    if expected_source_ratio < 0.75:
        flags.append("missed_expected_source")
    if citations and len(unique_citations) < max(1, len(expected_sources) // 2):
        flags.append("weak_source_diversity")
    if not citations and expected_sources:
        flags.append("weak_grounding")
    if code_line_ratio > 0.55 and not has_synthesis_section:
        flags.append("snippet_dump_without_synthesis")
    if word_count > 1400 and expected_term_ratio < 0.8:
        flags.append("verbosity_without_value")
    if junk_artifacts:
        flags.append("junk_artifact")
    if unsupported_risk:
        flags.append("unsupported_claim_risk")
    if product_benefit <= 2:
        flags.append("weak_product_value")

    # Weight grounded quality over artifacts.
    grounded_quality_total = (
        correctness * 1.35
        + grounding * 1.55
        + source_coverage * 1.15
        + completeness * 1.25
        + synthesis * 1.05
        + communication * 0.65
    )
    overall_total = grounded_quality_total + product_benefit * 1.75

    notes = [
        f"expected_terms={len(term_hits)}/{len(expected_terms)}",
        f"expected_sources={len(source_hits)}/{len(expected_sources)}",
        f"citations={len(citations)} unique_citations={len(unique_citations)}",
        f"synthesis={'yes' if has_synthesis_section or has_cross_source else 'no'}",
        f"artifacts=source_map:{has_source_map}, relevant_pages:{has_relevant_pages}, inventory:{has_artifact_inventory}, query:{has_query_artifact}",
    ]
    if junk_artifacts:
        notes.append(f"junk_artifacts={junk_artifacts}")

    raw_metrics = {
        "word_count": word_count,
        "expected_term_hits": term_hits,
        "expected_source_hits": source_hits,
        "citations": len(citations),
        "unique_citations": unique_citations,
        "refs": len(refs),
        "junk_refs": junk_artifacts,
        "code_line_ratio": round(code_line_ratio, 3),
        "expected_term_ratio": round(expected_term_ratio, 3),
        "expected_source_ratio": round(expected_source_ratio, 3),
    }

    return ArmScore(
        correctness=correctness,
        grounding=grounding,
        source_coverage=source_coverage,
        completeness=completeness,
        synthesis=synthesis,
        product_benefit=product_benefit,
        communication=communication,
        grounded_quality_total=round(grounded_quality_total, 2),
        overall_total=round(overall_total, 2),
        evidence_notes=notes,
        failure_flags=flags,
        raw_metrics=raw_metrics,
    )


def choose_winner(a: ArmScore, b: ArmScore) -> tuple[str, str, str, bool]:
    q_delta = a.grounded_quality_total - b.grounded_quality_total
    overall_delta = a.overall_total - b.overall_total
    product_delta = a.product_benefit - b.product_benefit
    severe_a = any(f in a.failure_flags for f in ["unsupported_claim_risk", "weak_grounding"]) and a.grounding <= 2
    severe_b = any(f in b.failure_flags for f in ["unsupported_claim_risk", "weak_grounding"]) and b.grounding <= 2

    if severe_a and not severe_b:
        return "B", "high", "A has severe grounding/unsupported-claim risk.", False
    if severe_b and not severe_a:
        return "A", "high", "B has severe grounding/unsupported-claim risk.", False

    if abs(q_delta) >= 1.5:
        winner = "A" if q_delta > 0 else "B"
        conf = "high" if abs(q_delta) >= 4 else "medium"
        return winner, conf, f"Grounded-quality delta is decisive ({q_delta:+.2f} A-B).", False

    if abs(overall_delta) >= 2.0 and abs(q_delta) < 1.5:
        winner = "A" if overall_delta > 0 else "B"
        conf = "medium"
        return winner, conf, f"Grounded quality is close; product/artifact benefit breaks tie (overall delta {overall_delta:+.2f}, product delta {product_delta:+}).", True

    if abs(q_delta) < 0.75 and abs(overall_delta) < 1.25:
        return "tie", "low", "Differences are too small for a reliable preference.", True

    winner = "A" if overall_delta > 0 else "B"
    return winner, "low", f"Small overall edge only ({overall_delta:+.2f}); should be human-reviewed.", True


def as_dict(score: ArmScore) -> dict[str, Any]:
    return {
        "correctness": score.correctness,
        "grounding": score.grounding,
        "source_coverage": score.source_coverage,
        "completeness": score.completeness,
        "synthesis": score.synthesis,
        "product_benefit": score.product_benefit,
        "communication": score.communication,
        "grounded_quality_total": score.grounded_quality_total,
        "overall_total": score.overall_total,
        "raw_metrics": score.raw_metrics,
    }


def judge_packet(packet: Path, run_root: Path) -> dict[str, Any]:
    packet_id, answer_a, answer_b = parse_packet(packet)
    case_path = run_root / "runs" / packet_id / "case.json"
    if not case_path.exists():
        raise FileNotFoundError(f"Missing case file for {packet_id}: {case_path}")
    case = json.loads(case_path.read_text(errors="ignore"))
    a = score_answer(answer_a, case)
    b = score_answer(answer_b, case)
    winner, confidence, reason, needs_human = choose_winner(a, b)
    return {
        "packet_id": packet_id,
        "question": case.get("question", ""),
        "winner": winner,
        "confidence": confidence,
        "scores": {"A": as_dict(a), "B": as_dict(b)},
        "failure_flags": {"A": a.failure_flags, "B": b.failure_flags},
        "evidence_notes": {"A": a.evidence_notes, "B": b.evidence_notes},
        "decisive_reason": reason,
        "needs_human_review": needs_human,
    }


def aggregate(results: list[dict[str, Any]], blind_key: dict[str, dict[str, str]] | None) -> dict[str, Any]:
    blind_counts = Counter(r["winner"] for r in results)
    identity_counts = Counter()
    confidence_counts = Counter(r["confidence"] for r in results)
    human_review = [r["packet_id"] for r in results if r["needs_human_review"]]
    deltas = []
    by_case = []
    flag_counts = {"A": Counter(), "B": Counter(), "raw_context": Counter(), "wiki": Counter()}

    for r in results:
        a_total = r["scores"]["A"]["overall_total"]
        b_total = r["scores"]["B"]["overall_total"]
        a_q = r["scores"]["A"]["grounded_quality_total"]
        b_q = r["scores"]["B"]["grounded_quality_total"]
        deltas.append({"packet_id": r["packet_id"], "quality_delta_A_minus_B": round(a_q - b_q, 2), "overall_delta_A_minus_B": round(a_total - b_total, 2)})
        for arm in ["A", "B"]:
            flag_counts[arm].update(r["failure_flags"][arm])

        identity_winner = None
        if blind_key and r["winner"] in {"A", "B"}:
            identity_winner = blind_key.get(r["packet_id"], {}).get(r["winner"])
            if identity_winner:
                identity_counts[identity_winner] += 1
        elif r["winner"] in {"tie", "neither"}:
            identity_counts[r["winner"]] += 1

        if blind_key:
            key = blind_key.get(r["packet_id"], {})
            for arm in ["A", "B"]:
                ident = key.get(arm)
                if ident in {"raw_context", "wiki"}:
                    flag_counts[ident].update(r["failure_flags"][arm])

        by_case.append({
            "packet_id": r["packet_id"],
            "blind_winner": r["winner"],
            "identity_winner": identity_winner,
            "confidence": r["confidence"],
            "quality_delta_A_minus_B": round(a_q - b_q, 2),
            "overall_delta_A_minus_B": round(a_total - b_total, 2),
            "needs_human_review": r["needs_human_review"],
            "decisive_reason": r["decisive_reason"],
        })

    avg_scores = {"A": defaultdict(float), "B": defaultdict(float)}
    dims = ["correctness", "grounding", "source_coverage", "completeness", "synthesis", "product_benefit", "communication", "grounded_quality_total", "overall_total"]
    for r in results:
        for arm in ["A", "B"]:
            for dim in dims:
                avg_scores[arm][dim] += r["scores"][arm][dim]
    for arm in ["A", "B"]:
        for dim in dims:
            avg_scores[arm][dim] = round(avg_scores[arm][dim] / max(len(results), 1), 2)

    return {
        "runs": len(results),
        "blind_winner_counts": dict(blind_counts),
        "identity_winner_counts_after_key": dict(identity_counts),
        "confidence_counts": dict(confidence_counts),
        "avg_blind_scores": {arm: dict(vals) for arm, vals in avg_scores.items()},
        "human_review_count": len(human_review),
        "human_review_cases": human_review,
        "flag_counts": {k: dict(v) for k, v in flag_counts.items()},
        "cases": by_case,
    }


def write_report(out_dir: Path, summary: dict[str, Any], results: list[dict[str, Any]]) -> None:
    lines = [
        "# Critical RAG Judge Agent Report",
        "",
        "This report was generated by `evals/critical_judge_agent.py` using the spec in `agents/critical-rag-judge/SPEC.md`.",
        "It is a deterministic critical pre-judge, not a replacement for independent human/LLM blind judging.",
        "",
        "## Summary",
        f"- Runs: {summary['runs']}",
        f"- Blind winner counts: {summary['blind_winner_counts']}",
        f"- Identity winner counts after opening key: {summary['identity_winner_counts_after_key']}",
        f"- Confidence counts: {summary['confidence_counts']}",
        f"- Human-review cases: {summary['human_review_count']}",
        "",
        "## Average blind scores",
    ]
    for arm, vals in summary["avg_blind_scores"].items():
        lines.append(f"- {arm}: " + ", ".join(f"{k}={v}" for k, v in vals.items()))
    lines.extend(["", "## Failure flag counts after key"])
    for ident in ["raw_context", "wiki", "A", "B"]:
        lines.append(f"- {ident}: {summary['flag_counts'].get(ident, {})}")
    lines.extend(["", "## Per-case results"])
    for c in summary["cases"]:
        lines.append(
            f"- {c['packet_id']}: blind={c['blind_winner']} identity={c['identity_winner']} "
            f"confidence={c['confidence']} qΔ(A-B)={c['quality_delta_A_minus_B']} "
            f"overallΔ(A-B)={c['overall_delta_A_minus_B']} review={c['needs_human_review']} — {c['decisive_reason']}"
        )
    lines.extend(["", "## Caveat", "", "The blind key is used only after judging for aggregate identity reporting. For gold-standard validation, have Dor or an independent LLM judge the packets without this script's identity results."])
    (out_dir / "CRITICAL_JUDGE_REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="serious validation output dir containing blind_packets/runs/blind_key.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-key", action="store_true", help="do not use blind_key.json for identity aggregation")
    args = parser.parse_args()

    input_dir = args.input
    packet_dir = input_dir / "blind_packets"
    packets = sorted(packet_dir.glob("*.md"))
    if not packets:
        raise SystemExit(f"No packets found under {packet_dir}")

    args.output.mkdir(parents=True, exist_ok=True)
    results = [judge_packet(packet, input_dir) for packet in packets]
    blind_key = None
    if not args.no_key:
        key_path = input_dir / "blind_key.json"
        if key_path.exists():
            blind_key = json.loads(key_path.read_text(errors="ignore"))
    summary = aggregate(results, blind_key)

    (args.output / "critical_judge_results.json").write_text(json.dumps(results, indent=2, sort_keys=True))
    (args.output / "critical_judge_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    write_report(args.output, summary, results)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
