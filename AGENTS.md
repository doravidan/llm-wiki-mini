# Agent Integration Guide

This repository is designed so an end user does **not** need to install or operate LLM Wiki Mini directly. The expected flow is:

> The user tells an AI coding/research agent: "Use LLM Wiki Mini on this project."
>
> The agent clones this repo, runs it from source with `PYTHONPATH`, builds a local wiki in the target project, and answers with source-grounded evidence.

## Agent contract

When asked to use LLM Wiki Mini, the agent should:

1. Clone or reuse this repository in an agent-controlled tools/cache directory.
2. Run it from source; do not require the human user to install a Python package globally.
3. Create generated wiki artifacts inside the target project under `.llm-wiki/` unless the user asks for a different path.
4. Ingest only relevant project files first; avoid committing generated `.llm-wiki/` output unless explicitly requested.
5. Answer using the generated query page, source map, and evidence snippets.
6. Report exact files used and the generated query artifact path.

## No-install command pattern

From any target project, assuming this repo is cloned at `$LLM_WIKI_MINI_REPO`:

```bash
export LLM_WIKI_MINI_REPO=/path/to/llm-wiki-mini
export TARGET_PROJECT=/path/to/project
export WIKI_DIR="$TARGET_PROJECT/.llm-wiki"

PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli init "$WIKI_DIR"
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ingest "$WIKI_DIR" "$TARGET_PROJECT/README.md" --title README.md
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ask "$WIKI_DIR" "How is this project structured?"
```

This works without `pip install`; Python imports the package directly from the cloned repository.

## Recommended agent workflow

### 1. Discover likely source files

Prefer files that describe architecture, flows, APIs, product behavior, and critical code paths:

- `README.md`, `docs/**/*.md`, `AGENTS.md`
- backend/API files
- client entry points
- migrations/schema files
- auth/payment/storage/release files
- tests that encode expected behavior

Skip by default:

- `.git/`, `.venv/`, `node_modules/`, build outputs
- generated eval/wiki runs
- binary assets
- secret files such as `.env*`, private keys, certificates

### 2. Ingest a focused source set

Start with 5-20 high-signal files, then expand only if the answer is missing evidence.

```bash
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli init "$WIKI_DIR"

while IFS= read -r file; do
  PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ingest \
    "$WIKI_DIR" \
    "$file" \
    --title "$(basename "$file")"
done < /tmp/llm-wiki-sources.txt
```

### 3. Ask and cite evidence

```bash
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ask \
  "$WIKI_DIR" \
  "What should I change to implement <feature>?"
```

The answer should include:

- source-backed summary
- source map
- evidence snippets with `raw/articles/...` anchors
- generated query page in `$WIKI_DIR/queries/`

### 4. Keep the target repo clean

Before committing target-project work:

```bash
git status --short
```

Do not commit `.llm-wiki/` unless the user explicitly wants durable wiki artifacts in their repo. If the target repo does not ignore it, add `.llm-wiki/` to the target repo's `.gitignore` after confirming that is desired.

## Copy/paste prompt for end users

```text
Use LLM Wiki Mini to understand this repository before implementing the task.
Do not ask me to install anything. Clone or reuse https://github.com/doravidan/llm-wiki-mini in your own tools/cache area, run it from source with PYTHONPATH, create a local .llm-wiki/ folder, ingest the relevant architecture/code/test files, then answer with source evidence and implement the change.
```

## Copy/paste prompt for agents

```text
You are implementing a change in a target repository. First use LLM Wiki Mini as an agent-side source-grounded project memory tool:

1. If unavailable, clone https://github.com/doravidan/llm-wiki-mini into an agent-controlled tools/cache directory.
2. Do not require the human user to install anything.
3. Run commands with: PYTHONPATH=/path/to/llm-wiki-mini python -m llm_wiki_mini.cli ...
4. Create the wiki at <target-repo>/.llm-wiki.
5. Ingest focused files relevant to the task.
6. Ask the implementation question.
7. Use the answer's source map/evidence while editing.
8. Keep generated wiki artifacts uncommitted unless explicitly requested.
```

## Verification command for agents

After cloning this tool, run:

```bash
PYTHONPATH=/path/to/llm-wiki-mini python -m pytest /path/to/llm-wiki-mini/tests -q
```

Expected: all tests pass.
