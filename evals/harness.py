from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json, re, shutil
from typing import Any

from llm_wiki_mini.core import init_wiki, ingest_file, ask, keywords

@dataclass
class EvalCase:
    case_id: str
    question: str
    sources: dict[str, str]
    expected_terms: list[str]
    expected_sources: list[str]
    notes: str = ""

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")

def norm(s: str) -> str:
    return s.lower()

def source_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]

def overlap_score(sentence: str, query_terms: set[str]) -> int:
    sent_terms = set(keywords(sentence, 30)) | {w.lower() for w in WORD_RE.findall(sentence)}
    return len(query_terms & sent_terms)

def no_wiki_answer(case: EvalCase) -> str:
    # Deliberately corpus-free. This models a generic answer when durable memory is absent.
    return (
        f"Without the source corpus, a likely answer is: {case.question} relates to organizing knowledge, "
        "summarizing material, and reducing repeated work. Verify details against sources."
    )

def raw_context_answer(case: EvalCase) -> str:
    qterms = set(keywords(case.question, 20)) | {w.lower() for w in WORD_RE.findall(case.question)}
    ranked: list[tuple[int, str, str]] = []
    for name, text in case.sources.items():
        for sent in source_sentences(text):
            score = overlap_score(sent, qterms | set(case.expected_terms))
            if score:
                ranked.append((score, name, sent))
    ranked.sort(reverse=True, key=lambda x: x[0])
    if not ranked:
        return "No relevant source sentences found."
    lines = ["Raw-context answer based on the supplied source files:"]
    for _, name, sent in ranked[:6]:
        lines.append(f"- [{name}] {sent}")
    return "\n".join(lines)

def wiki_answer(case: EvalCase, run_dir: Path) -> tuple[str, Path]:
    wiki = run_dir / "wiki"
    init_wiki(wiki)
    raw_dir = run_dir / "raw"
    for source_path in sorted(raw_dir.glob("*")):
        ingest_file(wiki, source_path, source_path.name)
    answer = ask(wiki, case.question)
    # Add explicit page/source inventory so this condition can expose provenance if the wiki has it.
    pages = sorted(str(p.relative_to(wiki)) for p in wiki.glob("**/*.md"))
    answer += "\n\nWiki inventory:\n" + "\n".join(f"- {p}" for p in pages)
    return answer, wiki

def _term_forms(text: str) -> set[str]:
    forms=set()
    for w in WORD_RE.findall(text.lower()):
        forms.add(w)
        if w.endswith('s') and len(w)>4:
            forms.add(w[:-1])
    return forms

def _has_term(text: str, term: str) -> bool:
    low=text.lower()
    t=term.lower()
    if t in low:
        return True
    # Robustness for plural/singular and punctuation variants: "buckets" should
    # match "bucket", and hyphenated identifiers are still checked literally above.
    term_forms=_term_forms(t)
    text_forms=_term_forms(low)
    return bool(term_forms & text_forms)

def score_answer(answer: str, case: EvalCase) -> dict[str, Any]:
    low = norm(answer)
    # Split durable navigation artifacts from the actual answer/evidence. This prevents
    # source-map/inventory-only mentions from inflating strict answer quality.
    answer_body = re.split(r"\n## Source map\n|\nWiki inventory:\n", answer, maxsplit=1)[0]
    body_low = norm(answer_body)
    term_hits = [t for t in case.expected_terms if _has_term(answer, t)]
    body_term_hits = [t for t in case.expected_terms if _has_term(answer_body, t)]
    source_hits = [s for s in case.expected_sources if norm(s) in low]
    body_source_hits = [s for s in case.expected_sources if norm(s) in body_low]
    # 1-5 scale per metric, deterministic and transparent.
    accuracy = min(5, 1 + round(4 * len(body_term_hits) / max(1, len(case.expected_terms))))
    coverage = min(5, 1 + round(4 * len(term_hits) / max(1, len(case.expected_terms))))
    provenance = min(5, 1 + round(4 * len(body_source_hits) / max(1, len(case.expected_sources))))
    synthesis_markers = sum(1 for token in ["because", "therefore", "so", "across", "compare", "both", "while"] if token in body_low)
    synthesis = min(5, 1 + synthesis_markers + (1 if len(body_source_hits) > 1 else 0))
    reuse_markers = sum(1 for token in ["wiki inventory", "relevant wiki pages", "source map", "^[raw/articles", "[["] if token in low)
    reuse = min(5, 1 + reuse_markers)
    strict_total = round(accuracy + coverage + provenance + synthesis, 2)
    usefulness = round((accuracy + coverage + provenance + synthesis + reuse) / 5, 2)
    total = round(strict_total + reuse + usefulness, 2)
    return {
        "accuracy": accuracy,
        "coverage": coverage,
        "synthesis": synthesis,
        "provenance": provenance,
        "reuse": reuse,
        "strict_total": strict_total,
        "usefulness": usefulness,
        "total": total,
        "term_hits": term_hits,
        "body_term_hits": body_term_hits,
        "source_hits": source_hits,
        "body_source_hits": body_source_hits,
    }

def write_report(case: EvalCase, answers: dict[str, str], scores: dict[str, dict[str, Any]], run_dir: Path) -> Path:
    report = run_dir / "report.md"
    winner = max(scores, key=lambda arm: scores[arm]["total"])
    strict_winner = max(scores, key=lambda arm: scores[arm]["strict_total"])
    lines = [
        f"# Eval: {case.case_id}", "",
        "## Question", case.question, "",
        "## Notes", case.notes or "n/a", "",
        "## Scores",
    ]
    for arm, score in scores.items():
        lines.append(f"- {arm}: total {score['total']} | strict {score['strict_total']} | accuracy {score['accuracy']} | coverage {score['coverage']} | synthesis {score['synthesis']} | provenance {score['provenance']} | reuse {score['reuse']} | usefulness {score['usefulness']}")
    lines += ["", "## Winner", winner, "", "## Strict Quality Winner", strict_winner, "", "## Answers"]
    for arm, answer in answers.items():
        lines += [f"### {arm}", answer, ""]
    report.write_text("\n".join(lines), encoding="utf-8")
    return report

def run_case(case: EvalCase, output_root: str | Path) -> dict[str, Any]:
    output_root = Path(output_root)
    run_dir = output_root / case.case_id
    if run_dir.exists():
        shutil.rmtree(run_dir)
    (run_dir / "raw").mkdir(parents=True)
    (run_dir / "answers").mkdir()
    for name, body in case.sources.items():
        (run_dir / "raw" / name).write_text(body, encoding="utf-8")

    answers: dict[str, str] = {
        "no_wiki": no_wiki_answer(case),
        "raw_context": raw_context_answer(case),
    }
    answers["wiki"], wiki_path = wiki_answer(case, run_dir)
    scores = {arm: score_answer(answer, case) for arm, answer in answers.items()}
    for arm, answer in answers.items():
        (run_dir / "answers" / f"{arm}.md").write_text(answer, encoding="utf-8")
    (run_dir / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (run_dir / "case.json").write_text(json.dumps(asdict(case), indent=2), encoding="utf-8")
    report = write_report(case, answers, scores, run_dir)
    return {
        "case_id": case.case_id,
        "answers": answers,
        "scores": scores,
        "paths": {"run_dir": str(run_dir), "wiki": str(wiki_path), "report": str(report)},
        "winner": max(scores, key=lambda arm: scores[arm]["total"]),
        "strict_winner": max(scores, key=lambda arm: scores[arm]["strict_total"]),
    }
