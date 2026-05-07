# Agent-First Usage

LLM Wiki Mini is intended to be used by agents on behalf of end users.

The user should not need to install a package, learn a CLI, or manage generated artifacts. Instead, an AI coding/research agent can clone the tool, run it directly from source, and use the generated wiki/query/source-map artifacts as project memory while completing the user's implementation task.

## End-user instruction

Tell your agent:

```text
Use LLM Wiki Mini before implementing this. Do not ask me to install anything. Clone or reuse https://github.com/doravidan/llm-wiki-mini yourself, run it from source with PYTHONPATH, create .llm-wiki/ locally in this repo, ingest the relevant source files, and use the source-backed answer/query page while implementing.
```

## Agent-side implementation recipe

```bash
# Agent-controlled cache/tool area, not the user's project dependencies.
TOOLS_DIR="${TOOLS_DIR:-$HOME/.cache/agent-tools}"
LLM_WIKI_MINI_REPO="$TOOLS_DIR/llm-wiki-mini"
TARGET_PROJECT="/path/to/user/project"
WIKI_DIR="$TARGET_PROJECT/.llm-wiki"

mkdir -p "$TOOLS_DIR"
if [ ! -d "$LLM_WIKI_MINI_REPO/.git" ]; then
  git clone https://github.com/doravidan/llm-wiki-mini "$LLM_WIKI_MINI_REPO"
fi

PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli init "$WIKI_DIR"
```

Then ingest focused files:

```bash
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ingest "$WIKI_DIR" "$TARGET_PROJECT/README.md" --title README.md
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ingest "$WIKI_DIR" "$TARGET_PROJECT/path/to/relevant_file.py" --title relevant_file.py
```

Ask the task question:

```bash
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ask "$WIKI_DIR" \
  "What files and behavior matter for implementing <user task>?"
```

## What agents should return to users

- Brief implementation-relevant synthesis.
- Source files consulted.
- Query artifact path under `.llm-wiki/queries/`.
- Edits made and tests run.

## What agents should not do

- Do not require the human to run `pip install`.
- Do not add LLM Wiki Mini as an application dependency of the target project unless explicitly requested.
- Do not commit `.llm-wiki/` output unless explicitly requested.
- Do not ingest secret files (`.env*`, private keys, certs) or generated dependency/build folders.

## Why this is agent-friendly

- Runs from a cloned source checkout with `PYTHONPATH`; no package install required.
- Produces local markdown artifacts that agents can read with normal file tools.
- Provides source maps and evidence anchors so the agent's implementation reasoning is auditable.
- Keeps project memory reusable across multiple agent tasks without depending on external services.
