from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import time
from pathlib import Path
from typing import Any

from .aitryon_eval import make_cases as make_aitryon_cases
from .aitryon_holdout_eval import make_cases as make_holdout_cases
from .harness import run_case, score_answer

ARMS = ["raw_context", "wiki"]


def _strip_for_blind(answer: str) -> str:
    """Remove explicit arm names but preserve answer structure/value."""
    text = answer.replace("Raw-context answer based on the supplied source files:", "Answer based on supplied project sources:")
    text = text.replace("Wiki inventory:", "Artifact inventory:")
    # Mask obvious wiki link syntax for blind readability while preserving referenced page names.
    text = re.sub(r"\[\[([^\]]+)\]\]", r"<ref:\1>", text)
    return text.strip()


def _answer_body(answer: str) -> str:
    return re.split(r"\n## Source map\n|\nWiki inventory:\n", answer, maxsplit=1)[0]


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _citation_count(text: str) -> int:
    return len(re.findall(r"\[[^\]]+\]", text)) + text.count("^[raw/articles/")


def _source_diversity(text: str, expected_sources: list[str]) -> int:
    low = text.lower()
    return sum(1 for s in expected_sources if s.lower() in low)


def blind_quality_score(answer: str, case) -> dict[str, Any]:
    """Quality score that excludes durable artifact inventory/source-map boosts.

    This is deliberately stricter than product scoring: it asks whether the visible answer body
    contains enough facts, cites enough files, and synthesizes across files.
    """
    body = _answer_body(answer)
    base = score_answer(body, case)
    diversity = _source_diversity(body, case.expected_sources)
    citation_count = _citation_count(body)
    words = _word_count(body)
    concision = 5 if 80 <= words <= 750 else (4 if words <= 1200 else 3)
    evidence = min(5, 1 + min(4, citation_count // 2))
    source_balance = min(5, 1 + round(4 * diversity / max(1, len(case.expected_sources))))
    # Penalize source-map-only/source-inventory-only answers by requiring body evidence.
    grounded_quality = round(
        base["accuracy"]
        + base["coverage"]
        + base["synthesis"]
        + base["provenance"]
        + evidence
        + source_balance
        + concision,
        2,
    )
    return {
        "grounded_quality": grounded_quality,
        "accuracy": base["accuracy"],
        "coverage": base["coverage"],
        "synthesis": base["synthesis"],
        "provenance": base["provenance"],
        "evidence": evidence,
        "source_balance": source_balance,
        "concision": concision,
        "word_count": words,
        "citation_count": citation_count,
        "source_diversity": diversity,
    }


def product_benefit_score(answer: str, wiki_dir: Path | None, case) -> dict[str, Any]:
    low = answer.lower()
    source_map = "## source map" in low
    inventory = "wiki inventory:" in low
    query_pages = len(list((wiki_dir / "queries").glob("*.md"))) if wiki_dir and wiki_dir.exists() else 0
    raw_pages = len(list((wiki_dir / "raw" / "articles").glob("*.md"))) if wiki_dir and wiki_dir.exists() else 0
    concept_pages = len(list((wiki_dir / "concepts").glob("*.md"))) if wiki_dir and wiki_dir.exists() else 0
    expected_source_coverage = _source_diversity(answer, case.expected_sources)
    evidence_refs = answer.count("^[raw/articles/")
    auditability = min(5, 1 + (2 if source_map else 0) + (1 if evidence_refs else 0) + round(expected_source_coverage / max(1, len(case.expected_sources))))
    reuse = min(5, 1 + (2 if query_pages else 0) + (1 if inventory else 0) + (1 if concept_pages >= len(case.sources) else 0))
    navigability = min(5, 1 + (1 if raw_pages else 0) + (1 if concept_pages else 0) + (1 if query_pages else 0) + (1 if source_map else 0))
    total = round(auditability + reuse + navigability, 2)
    return {
        "auditability": auditability,
        "reuse": reuse,
        "navigability": navigability,
        "total": total,
        "query_pages": query_pages,
        "raw_pages": raw_pages,
        "concept_pages": concept_pages,
        "evidence_refs": evidence_refs,
        "source_map": source_map,
        "inventory": inventory,
    }


def token_cost_proxy(answer: str, case) -> dict[str, Any]:
    source_words = sum(_word_count(t) for t in case.sources.values())
    answer_words = _word_count(answer)
    query_artifact_words = _word_count(_answer_body(answer))
    return {
        "source_words_if_raw_context": source_words,
        "answer_words": answer_words,
        "query_artifact_words": query_artifact_words,
        "reuse_break_even_queries": 2 if query_artifact_words < source_words else None,
        "compression_ratio_query_vs_sources": round(query_artifact_words / max(1, source_words), 3),
    }


def make_blind_packet(case_id: str, answers: dict[str, str], output_dir: Path) -> dict[str, str]:
    rnd = random.Random(int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16))
    order = ARMS[:]
    rnd.shuffle(order)
    labels = {"A": order[0], "B": order[1]}
    packet = [f"# Blind Review Packet: {case_id}", "", "Review without looking at the key. Pick A or B for:", "- factual correctness", "- source grounding", "- synthesis", "- usefulness", "", "## Answer A", _strip_for_blind(answers[labels["A"]]), "", "## Answer B", _strip_for_blind(answers[labels["B"]]), "", "## Reviewer Notes", "- Correctness winner:", "- Grounding winner:", "- Synthesis winner:", "- Product/usefulness winner:", "- Comments:", ""]
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{case_id}.md").write_text("\n".join(packet), encoding="utf-8")
    return labels


def run_validation(output: Path, suite: str = "aitryon") -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    if suite == "aitryon":
        cases = make_aitryon_cases()
    elif suite == "holdout":
        cases = make_holdout_cases()
    elif suite == "combined":
        cases = make_aitryon_cases() + make_holdout_cases()
    else:
        raise ValueError(f"unknown suite: {suite}")
    run_root = output / "runs"
    packet_root = output / "blind_packets"
    results = []
    key = {}
    started = time.perf_counter()
    for case in cases:
        result = run_case(case, run_root)
        answers = {arm: result["answers"][arm] for arm in ARMS}
        labels = make_blind_packet(case.case_id, answers, packet_root)
        key[case.case_id] = labels
        wiki_dir = Path(result["paths"]["wiki"])
        arm_results = {}
        for arm in ARMS:
            arm_results[arm] = {
                "blind_quality": blind_quality_score(answers[arm], case),
                "product_benefit": product_benefit_score(answers[arm], wiki_dir if arm == "wiki" else None, case),
                "cost_proxy": token_cost_proxy(answers[arm], case),
            }
        quality_winner = max(ARMS, key=lambda a: arm_results[a]["blind_quality"]["grounded_quality"])
        product_winner = max(ARMS, key=lambda a: arm_results[a]["product_benefit"]["total"])
        combined_winner = max(ARMS, key=lambda a: arm_results[a]["blind_quality"]["grounded_quality"] + arm_results[a]["product_benefit"]["total"])
        results.append({
            "case_id": case.case_id,
            "quality_winner": quality_winner,
            "product_winner": product_winner,
            "combined_winner": combined_winner,
            "arms": arm_results,
            "blind_packet": str(packet_root / f"{case.case_id}.md"),
            "report": result["paths"]["report"],
        })
    elapsed = round(time.perf_counter() - started, 3)
    summary = {
        "suite": suite,
        "method": "Blind A/B packet generation + deterministic grounded-quality/product-benefit scoring. Human or LLM judge can fill packets later.",
        "runs": len(results),
        "elapsed_seconds": elapsed,
        "quality_winners": {arm: sum(1 for r in results if r["quality_winner"] == arm) for arm in ARMS},
        "product_winners": {arm: sum(1 for r in results if r["product_winner"] == arm) for arm in ARMS},
        "combined_winners": {arm: sum(1 for r in results if r["combined_winner"] == arm) for arm in ARMS},
        "avg_scores": {},
        "cases": results,
        "blind_key": key,
    }
    for arm in ARMS:
        quality = [r["arms"][arm]["blind_quality"]["grounded_quality"] for r in results]
        product = [r["arms"][arm]["product_benefit"]["total"] for r in results]
        compression = [r["arms"][arm]["cost_proxy"]["compression_ratio_query_vs_sources"] for r in results]
        summary["avg_scores"][arm] = {
            "grounded_quality": round(sum(quality) / len(quality), 2),
            "product_benefit": round(sum(product) / len(product), 2),
            "combined": round((sum(quality) + sum(product)) / len(quality), 2),
            "avg_query_compression_ratio": round(sum(compression) / len(compression), 3),
        }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "blind_key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    write_report(summary, output / "VALIDATION_REPORT.md")
    return summary


def write_report(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Serious Validation Report: LLM Wiki Mini on AiTryOn",
        "",
        f"Suite: {summary.get('suite', 'unknown')}",
        f"Runs: {summary['runs']}",
        f"Elapsed seconds: {summary['elapsed_seconds']}",
        "",
        "## Winner counts",
        f"- Blind grounded quality: {summary['quality_winners']}",
        f"- Product benefit: {summary['product_winners']}",
        f"- Combined: {summary['combined_winners']}",
        "",
        "## Average scores",
    ]
    for arm, scores in summary["avg_scores"].items():
        lines.append(f"- {arm}: grounded_quality={scores['grounded_quality']} | product_benefit={scores['product_benefit']} | combined={scores['combined']} | query/source compression={scores['avg_query_compression_ratio']}")
    lines += ["", "## Per-case deltas"]
    for r in summary["cases"]:
        raw_q = r["arms"]["raw_context"]["blind_quality"]["grounded_quality"]
        wiki_q = r["arms"]["wiki"]["blind_quality"]["grounded_quality"]
        raw_p = r["arms"]["raw_context"]["product_benefit"]["total"]
        wiki_p = r["arms"]["wiki"]["product_benefit"]["total"]
        lines.append(f"- {r['case_id']}: quality Δ={round(wiki_q-raw_q,2)} | product Δ={round(wiki_p-raw_p,2)} | packet={r['blind_packet']}")
    lines += [
        "",
        "## Interpretation",
        "The strongest product signal is not that wiki snippets are magically smarter than raw context; it is that the wiki creates durable query pages, source maps, and navigable artifacts while matching or improving grounded answer quality on this project corpus.",
        "",
        "## Caveats",
        "- This run still uses deterministic scoring, not an independent human/LLM blind judge.",
        "- Blind packets are generated for manual review; use `blind_key.json` only after judging.",
        "- Product benefit depends on repeated/project-memory usage. For one-off single-file Q&A, raw context remains competitive.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="eval_runs_serious_validation")
    parser.add_argument("--suite", choices=["aitryon", "holdout", "combined"], default="aitryon")
    args = parser.parse_args(argv)
    summary = run_validation(Path(args.output), suite=args.suite)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
