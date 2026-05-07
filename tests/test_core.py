from llm_wiki_mini.core import init_wiki, ingest_file, ask

def test_ingest_creates_raw_concepts_index_and_answer(tmp_path):
    wiki=init_wiki(tmp_path/'wiki')
    src=tmp_path/'lecture.txt'
    src.write_text('Software 3.0 uses prompts, tools, memory, traces and evals. Agents need observability and replay.', encoding='utf-8')
    result=ingest_file(wiki, src, 'Software 3.0')
    assert 'software' in result['keywords']
    assert (wiki/'raw/articles/software-3-0.md').exists()
    assert '[[software-3-0]]' in (wiki/'index.md').read_text(encoding='utf-8')
    answer=ask(wiki, 'Why do agents need traces?')
    assert 'Based on' in answer and 'trace' in answer.lower()
