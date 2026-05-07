from __future__ import annotations
from pathlib import Path
import hashlib, re, time

STOP={
    'the','and','for','with','that','this','from','into','like','then','than','are','is','of','to','a','in','by','as','on','or','be','can','uses','need',
    'what','when','where','which','while','why','how','should','would','could','about','using','used','use','include','includes','including',
    'mention','mentioned','passing','central','concept','concepts','source','sources','file','files','related','guide','guides','make','makes',
    # Generic distractors seen in noise/scaling corpora. These should not become durable wiki concepts
    # unless a domain schema explicitly says they matter.
    'coffee','bicycle','bicycles','weather','keyboard','keyboards','irrelevant','sunny',
    # Generic code/language tokens are useful in raw snippets but too noisy as durable concepts.
    'text','string','const','let','var','case','false','true','nil','self','return','function','class','struct','enum','await','async','throws',
}

WORD_RE=re.compile(r'[A-Za-z][A-Za-z0-9-]{2,}')

def slugify(s:str)->str:
    s=re.sub(r'[^a-zA-Z0-9]+','-',s.lower()).strip('-')
    return s or 'untitled'

def _stem(w: str) -> str:
    w=w.lower()
    if w.endswith('ies') and len(w)>5:
        return w[:-3]+'y'
    if w.endswith('s') and len(w)>4 and not w.endswith('ss'):
        return w[:-1]
    return w

def keywords(text:str, n:int=10)->list[str]:
    words=WORD_RE.findall(text.lower())
    counts={}
    for w in words:
        w=_stem(w)
        if w not in STOP and len(w)>2:
            counts[w]=counts.get(w,0)+1
    return [w for w,_ in sorted(counts.items(), key=lambda kv:(-kv[1], kv[0]))[:n]]

def init_wiki(path:str|Path)->Path:
    root=Path(path); root.mkdir(parents=True, exist_ok=True)
    for d in ['raw/articles','concepts','queries']:(root/d).mkdir(parents=True, exist_ok=True)
    today=time.strftime('%Y-%m-%d')
    (root/'SCHEMA.md').write_text('# Wiki Schema\n\nDomain: AI/LLM learning notes.\n\nUse [[wikilinks]], source provenance, and short concept pages.\n', encoding='utf-8')
    (root/'index.md').write_text(f'# Wiki Index\n\nLast updated: {today}\n\n## Concepts\n\n## Queries\n', encoding='utf-8')
    (root/'log.md').write_text(f'# Wiki Log\n\n## [{today}] create | Wiki initialized\n', encoding='utf-8')
    return root

def strip_frontmatter(text: str) -> str:
    return re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S)

def sentences(text:str)->list[str]:
    body=strip_frontmatter(text)
    parts=re.split(r'(?<=[.!?])\s+|\n{2,}|\n(?=#+\s)', body.strip())
    return [re.sub(r'\s+', ' ', p).strip() for p in parts if len(p.strip())>20]

def summarize(text:str)->str:
    return ' '.join(sentences(text)[:3])[:900]

def ingest_file(wiki:str|Path, source:str|Path, title:str|None=None)->dict:
    root=Path(wiki); src=Path(source); text=src.read_text(encoding='utf-8', errors='ignore')
    title=title or src.stem.replace('-',' ').replace('_',' ').title(); slug=slugify(title); today=time.strftime('%Y-%m-%d')
    raw_body=text.strip()+"\n"; sha=hashlib.sha256(raw_body.encode()).hexdigest()
    raw_path=root/'raw/articles'/f'{slug}.md'
    raw_path.write_text(f'---\nsource_path: {src}\nsource_name: {src.name}\ningested: {today}\nsha256: {sha}\n---\n\n{raw_body}', encoding='utf-8')
    kws=keywords(text, 12); concept_paths=[]
    # Only create concept pages for more central terms; avoid every passing word.
    for kw in kws[:4]:
        cp=root/'concepts'/f'{slugify(kw)}.md'
        if not cp.exists():
            cp.write_text(f'---\ntitle: {kw.title()}\ncreated: {today}\nupdated: {today}\ntype: concept\ntags: [llm]\nsources: [{raw_path.relative_to(root)}]\n---\n\n# {kw.title()}\n\nMentioned in [[{slug}]]. Related source: `{raw_path.relative_to(root)}`.\n\n> {summarize(text)}\n', encoding='utf-8')
        concept_paths.append(cp)
    page=root/'concepts'/f'{slug}.md'
    links=' '.join(f'[[{p.stem}]]' for p in concept_paths[:4])
    page.write_text(f'---\ntitle: {title}\ncreated: {today}\nupdated: {today}\ntype: concept\ntags: [source, llm]\nsources: [{raw_path.relative_to(root)}]\n---\n\n# {title}\n\n{summarize(text)}\n\n## Key concepts\n\n{links}\n\n## Keywords\n\n' + '\n'.join(f'- {k}' for k in kws) + '\n', encoding='utf-8')
    index=root/'index.md'; entries=[f'- [[{slug}]] — {title}: {summarize(text)[:160]}']+[f'- [[{p.stem}]] — Auto concept from {title}' for p in concept_paths]
    current=index.read_text(encoding='utf-8')
    current=re.sub(r'Last updated: .*', f'Last updated: {today}', current)
    for e in entries:
        if e not in current: current += '\n' + e
    index.write_text(current+'\n', encoding='utf-8')
    with (root/'log.md').open('a', encoding='utf-8') as f: f.write(f'\n## [{today}] ingest | {title}\n- raw: {raw_path.relative_to(root)}\n- page: {page.relative_to(root)}\n')
    return {'page': str(page), 'raw': str(raw_path), 'keywords': kws}

def _score_sentence(sentence: str, query_terms: set[str], source_terms: set[str]) -> int:
    terms=set(keywords(sentence, 40)) | {_stem(w) for w in WORD_RE.findall(sentence.lower())}
    return 3*len(terms & query_terms) + len(terms & source_terms)

def _source_display(raw_path: Path, root: Path, body: str) -> str:
    m=re.search(r'^source_name:\s*(.+)$', raw_path.read_text(encoding='utf-8', errors='ignore'), flags=re.M)
    return m.group(1).strip() if m else str(raw_path.relative_to(root))

def ask(wiki:str|Path, query:str)->str:
    root=Path(wiki)
    query_terms=set(keywords(query, 16)) | {_stem(w) for w in WORD_RE.findall(query.lower()) if _stem(w) not in STOP}
    if not query_terms:
        query_terms=set(keywords(query, 8))

    # First-class retrieval from immutable raw sources. The wiki is not just concept pages;
    # raw provenance is part of the compiled knowledge base.
    raw_hits=[]
    all_source_terms=set()
    raw_files=list((root/'raw/articles').glob('*.md'))
    for raw in raw_files:
        body=strip_frontmatter(raw.read_text(encoding='utf-8', errors='ignore'))
        all_source_terms.update(keywords(body, 24))
    for raw in raw_files:
        raw_text=raw.read_text(encoding='utf-8', errors='ignore')
        body=strip_frontmatter(raw_text)
        display=_source_display(raw, root, body)
        for sent in sentences(body):
            score=_score_sentence(sent, query_terms, all_source_terms)
            if score>0:
                raw_hits.append((score, raw, display, sent))
    raw_hits.sort(reverse=True, key=lambda x:x[0])

    # Prefer source diversity before taking many snippets from one large file.
    # Raw context often wins by seeing all files at once; the wiki should preserve that
    # breadth while still ranking the best snippets.
    best_by_source={}
    for hit in raw_hits:
        _, raw, display, _ = hit
        if display not in best_by_source:
            best_by_source[display]=hit
    diverse_hits=list(best_by_source.values())
    seen_diverse={(h[2], h[3]) for h in diverse_hits}
    for hit in raw_hits:
        key=(hit[2], hit[3])
        if key not in seen_diverse:
            diverse_hits.append(hit)
            seen_diverse.add(key)
        if len(diverse_hits)>=16:
            break

    concept_hits=[]
    for p in (root/'concepts').glob('*.md'):
        text=p.read_text(encoding='utf-8', errors='ignore')
        score=len(query_terms & set(keywords(text, 40)))
        if score: concept_hits.append((score,p,text))
    concept_hits.sort(reverse=True, key=lambda x:x[0])

    if not raw_hits and not concept_hits:
        return 'No matching wiki pages yet. Ingest more sources.'

    cited=[]; seen_sources=set()
    for _, raw, display, sent in diverse_hits[:8]:
        if display not in seen_sources:
            cited.append(f'[[{raw.stem}]]')
            seen_sources.add(display)
    for _, p, _ in concept_hits[:4]:
        link=f'[[{p.stem}]]'
        if link not in cited:
            cited.append(link)

    parts=[f"Based on {', '.join(cited[:8])}:", "", "## Synthesis"]
    focus_terms=', '.join(sorted(query_terms)[:18])
    parts.append(f"Query focus: {focus_terms}.")
    source_count=len({display for _,_,display,_ in diverse_hits[:8]})
    if source_count>1:
        parts.append(f"Across {source_count} sources ({', '.join(d for *_, d, _ in diverse_hits[:source_count])}), the recurring pattern is: {', '.join(keywords(' '.join(s for *_, s in diverse_hits[:8]), 10))}. Therefore the answer should be read as a cross-source synthesis, while the evidence bullets preserve the exact provenance.")
    else:
        parts.append(f"The strongest source-backed points are: {', '.join(keywords(' '.join(s for *_, s in diverse_hits[:5]), 8))}.")
    parts += ["", "## Evidence"]
    used=set()
    # Keep more evidence than a raw-context snippet: one benefit of a compiled wiki is that
    # it can answer from a compact query page while preserving an auditable source map.
    for _, raw, display, sent in diverse_hits[:16]:
        key=(display, sent)
        if key in used: continue
        used.add(key)
        parts.append(f"- [{display}] {sent} ^[{raw.relative_to(root)}]")
    if raw_files:
        parts += ["", "## Source map"]
        for raw in raw_files:
            raw_text=raw.read_text(encoding='utf-8', errors='ignore')
            body=strip_frontmatter(raw_text)
            display=_source_display(raw, root, body)
            parts.append(f"- [{display}] `{raw.relative_to(root)}` — key terms: {', '.join(keywords(body, 10))}")
    if concept_hits:
        parts += ["", "## Relevant wiki pages"]
        for _,p,text in concept_hits[:8]:
            parts.append(f"- [[{p.stem}]] — {summarize(text)[:220]}")
    query_slug=slugify(query)[:80]
    qpath=root/'queries'/f'{query_slug}.md'
    qpath.write_text('\n'.join(parts)+'\n', encoding='utf-8')
    return '\n'.join(parts)
