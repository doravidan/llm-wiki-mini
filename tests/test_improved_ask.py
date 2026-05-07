from llm_wiki_mini.core import init_wiki, ingest_file, ask


def test_ask_uses_raw_sources_and_synthesizes_across_files(tmp_path):
    wiki = init_wiki(tmp_path / "wiki")
    a = tmp_path / "micrograd.md"
    b = tmp_path / "agent-evals.md"
    a.write_text("Micrograd teaches gradients, loss, and optimization with a tiny autograd engine.", encoding="utf-8")
    b.write_text("Agent evals test prompts, tools, memory, traces, and replay to debug regressions.", encoding="utf-8")
    ingest_file(wiki, a, "Micrograd")
    ingest_file(wiki, b, "Agent Evals")

    answer = ask(wiki, "Design a learning path from micrograd to agent evals")

    assert "Synthesis" in answer
    assert "raw/articles/micrograd.md" in answer
    assert "raw/articles/agent-evals.md" in answer
    assert "gradients" in answer.lower()
    assert "traces" in answer.lower()
