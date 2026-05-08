# LLM Wiki Mini

Local-first markdown knowledge compiler inspired by Karpathy-style LLM wiki workflows.

![LLM Wiki Mini turns raw repository chaos into agent-ready wiki memory](assets/llm-wiki-mini-flow.jpg)

The project ingests source files into a small auditable markdown wiki, answers questions from raw source evidence plus generated wiki artifacts, and includes a serious validation harness that compares wiki answers against raw-context baselines on real software-project cases.

## Why this exists

Raw context is strong for one-off questions. LLM Wiki Mini is designed for repeated project understanding where durable artifacts matter:

- source-grounded answers
- query pages that can be reused
- source maps and evidence references
- navigable markdown wiki pages
- blind A/B validation against raw-context answers
- critical judge reports that flag weak grounding, verbosity, and junk artifacts

## Agent-first usage: no end-user install

This project is meant to be used by AI agents on behalf of end users. The human should be able to say: "Use LLM Wiki Mini before implementing this," and the agent can clone this repo, run it from source, and create local wiki artifacts in the target project.

Copy/paste prompt for an agent:

```text
Use LLM Wiki Mini to understand this repository before implementing the task. Do not ask me to install anything. Clone or reuse https://github.com/doravidan/llm-wiki-mini in your own tools/cache area, run it from source with PYTHONPATH, create a local .llm-wiki/ folder, ingest relevant architecture/code/test files, then answer and implement using source-backed evidence.
```

No-install command pattern for agents:

```bash
export LLM_WIKI_MINI_REPO=/path/to/cloned/llm-wiki-mini
export TARGET_PROJECT=/path/to/user/project
export WIKI_DIR="$TARGET_PROJECT/.llm-wiki"

PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli init "$WIKI_DIR"
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ingest "$WIKI_DIR" "$TARGET_PROJECT/README.md" --title README.md
PYTHONPATH="$LLM_WIKI_MINI_REPO" python -m llm_wiki_mini.cli ask "$WIKI_DIR" "What files matter for this implementation task?"
```

See `AGENTS.md` and `docs/AGENT_USAGE.md` for the full agent contract.

## Optional developer install

Installation is optional and mainly for developers working on this package directly.

From this repository:

```bash
python -m pip install -e .
```

For development:

```bash
python -m pip install -e '.[dev]'
```

## CLI usage

```bash
llm-wiki-mini init ./wiki
llm-wiki-mini ingest ./wiki ./docs/architecture.md --title architecture.md
llm-wiki-mini ask ./wiki "How does auth work across the project?"
```

Equivalent module entry point:

```bash
python -m llm_wiki_mini.cli init ./wiki
```

## Python API

```python
from llm_wiki_mini.core import init_wiki, ingest_file, ask

wiki = init_wiki("./wiki")
ingest_file(wiki, "./docs/architecture.md", "architecture.md")
print(ask(wiki, "What are the key auth flows?"))
```

## Validation

Run unit tests:

```bash
PYTHONPATH=. python -m pytest -q
```

Run the synthetic/mini eval suite:

```bash
PYTHONPATH=. python -m evals.run_eval --output eval_runs
```

Run the AiTryOn serious validation suite if `/Users/doravidan/Projects/style-my-look` is available:

```bash
PYTHONPATH=. python -m evals.serious_validation \
  --suite combined \
  --output eval_runs_serious_combined
```

Run the critical judge over generated blind packets:

```bash
PYTHONPATH=. python -m evals.critical_judge_agent \
  --input eval_runs_serious_combined \
  --output eval_runs_critical_judge
```

The serious validation creates:

- `summary.json`
- `VALIDATION_REPORT.md`
- `blind_packets/*.md`
- `blind_key.json`
- per-case reports and wiki artifacts under `runs/`

Important: for human or independent LLM judgment, review the blind packets before opening `blind_key.json`.

## Latest local validation evidence

On the local AiTryOn/style-my-look corpus, the latest combined judged run produced:

- serious validation: wiki won 14/14 quality, 14/14 product benefit, 14/14 combined
- critical judge: wiki won 14/14 after blind-key reveal
- critical judge confidence: high on 14/14
- qualitative artifact check: 14 packets, blind key present, no qualitative problems
- unit tests: 4 passed before production-hardening additions; full suite should pass with `python -m pytest -q`

These are deterministic and rubric-based results, not a substitute for final human or independent LLM blind judging.

## Production hygiene

- `pyproject.toml` defines package metadata, console script, pytest config, and optional dev tooling.
- `.gitignore` excludes generated eval runs, caches, build artifacts, virtualenvs, and local env files.
- GitHub Actions CI runs tests on Python 3.11 and 3.12.
- No runtime network calls or external API keys are required by the core package.

## Project layout

```text
llm_wiki_mini/          core package and CLI
evals/                  validation harnesses and critical judge agent
agents/                 agent specs, including Critical RAG Judge
tests/                  unit and production hygiene tests
.github/workflows/      CI
```

## Caveats

- The core wiki compiler is intentionally small and deterministic.
- AiTryOn validation cases depend on local project files for full serious validation.
- Deterministic judge results are useful for regression testing but should be calibrated against human or independent LLM blind review before making strong external product claims.

## License

MIT. See `LICENSE`.
