from __future__ import annotations
import argparse, json
from pathlib import Path
from .harness import EvalCase, run_case

CASES = [
    EvalCase(
        case_id="single_source_software_3",
        question="Summarize Software 3.0 and list engineering implications.",
        sources={
            "karpathy-software-3.md": "Software 1.0 is code written by humans. Software 2.0 is neural network weights learned by optimization. Software 3.0 is natural language prompts and context programming large language models. Engineering implications include prompt management, tool integration, memory, evals, traces, and replay for debugging stochastic systems."
        },
        expected_terms=["software", "prompt", "tool", "memory", "eval", "trace", "replay", "debug"],
        expected_sources=["karpathy-software-3.md"],
        notes="Sanity check: wiki should not destroy single-source facts.",
    ),
    EvalCase(
        case_id="multi_source_learning_path",
        question="Design a learning path from micrograd to agent evals.",
        sources={
            "micrograd.md": "Micrograd teaches backpropagation with a tiny scalar autograd engine. It makes gradients, loss, and optimization visible.",
            "nanogpt.md": "NanoGPT teaches language modeling with tokenization, transformer blocks, training loops, and sampling on small corpora.",
            "agent-evals.md": "Agent evals test prompts, tools, memory, traces, and replay. They compare behavior across model or prompt versions and catch regressions.",
        },
        expected_terms=["micrograd", "gradient", "nanogpt", "tokenization", "training", "agent", "eval", "trace", "replay"],
        expected_sources=["micrograd.md", "nanogpt.md", "agent-evals.md"],
        notes="Multi-source synthesis should be the wiki's target use case.",
    ),
    EvalCase(
        case_id="contradiction_api_version",
        question="Which API recommendation should we follow and what changed?",
        sources={
            "api-old-2024.md": "In 2024 the service recommended API v1. API v1 used key-only authentication and did not support shared payment tokens. The old guide says to keep using v1 for compatibility.",
            "api-new-2026.md": "In 2026 the service recommends API v2. API v2 supports shared payment tokens, stricter authorization, and audit logs. The new guide says v1 is deprecated for new integrations.",
        },
        expected_terms=["2024", "2026", "v1", "v2", "deprecated", "shared", "token", "audit"],
        expected_sources=["api-old-2024.md", "api-new-2026.md"],
        notes="Contradiction/date handling should reveal whether the wiki preserves nuance.",
    ),
    EvalCase(
        case_id="ops_reliability_reuse",
        question="What are the recurring reliability issues and what should the on-call checklist include?",
        sources={
            "heartbeat.md": "Heartbeat notifications should be state-change driven to avoid noise. Alerts should include current route, cron status, and last successful run.",
            "api-tasks.md": "The /api/tasks endpoint intermittently times out while /board and /api/health return 200. Check logs first, then database latency, then gateway routing.",
            "cron.md": "Cron failures often look like stale task state. On-call should check scheduler logs, task queue depth, heartbeat status, and recent deploys before restarting services.",
        },
        expected_terms=["heartbeat", "state-change", "api", "tasks", "timeout", "logs", "cron", "queue", "routing"],
        expected_sources=["heartbeat.md", "api-tasks.md", "cron.md"],
        notes="Dor-realistic ops corpus: should reward reusable compiled notes.",
    ),
    EvalCase(
        case_id="scaling_noise",
        question="What are the central concepts, ignoring passing mentions?",
        sources={
            "core.md": "The central concepts are durable memory, provenance, semantic search, contradiction detection, and eval-driven iteration. Passing mentions include coffee, bicycles, and weather.",
            "noise-a.md": "Coffee coffee coffee. A passing mention says transformers exist but gives no detail. Weather is sunny.",
            "noise-b.md": "Bicycles and keyboards are irrelevant. Durable memory appears once as a real requirement for cross-session reuse.",
            "noise-c.md": "Provenance and contradiction detection are important because users need to verify claims and compare older sources with newer sources.",
        },
        expected_terms=["durable", "memory", "provenance", "semantic", "search", "contradiction", "eval"],
        expected_sources=["core.md", "noise-c.md"],
        notes="Noise test: current MVP keyword extraction may over-index on repeated irrelevant words.",
    ),
]

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="eval_runs")
    parser.add_argument("--case", action="append", help="Case id to run; can be repeated")
    args = parser.parse_args(argv)
    selected = [c for c in CASES if not args.case or c.case_id in args.case]
    output = Path(args.output)
    results = [run_case(case, output) for case in selected]
    summary = {
        "runs": len(results),
        "winners": {arm: sum(1 for r in results if r["winner"] == arm) for arm in ["no_wiki", "raw_context", "wiki"]},
        "strict_winners": {arm: sum(1 for r in results if r["strict_winner"] == arm) for arm in ["no_wiki", "raw_context", "wiki"]},
        "cases": [{"case_id": r["case_id"], "winner": r["winner"], "strict_winner": r["strict_winner"], "scores": r["scores"], "report": r["paths"]["report"]} for r in results],
    }
    output.mkdir(exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
