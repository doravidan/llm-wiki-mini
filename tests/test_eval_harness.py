from pathlib import Path

from evals.harness import EvalCase, run_case


def test_eval_harness_compares_baselines_and_wiki(tmp_path):
    case = EvalCase(
        case_id="mini",
        question="Why do Software 3.0 apps need traces?",
        sources={
            "lecture.md": "Software 3.0 apps use prompts, tools, memory, and evals. Agent behavior is stochastic, so traces and replay are needed for debugging.",
            "ops.md": "Trace logs preserve prompts, tool calls, outputs, latency, and errors so developers can audit agent failures.",
        },
        expected_terms=["trace", "replay", "debug", "tool", "prompt"],
        expected_sources=["lecture.md", "ops.md"],
    )

    result = run_case(case, tmp_path)

    assert set(result["answers"]) == {"no_wiki", "raw_context", "wiki"}
    assert result["scores"]["raw_context"]["total"] > result["scores"]["no_wiki"]["total"]
    assert result["scores"]["wiki"]["provenance"] >= result["scores"]["no_wiki"]["provenance"]
    assert Path(result["paths"]["report"]).exists()
