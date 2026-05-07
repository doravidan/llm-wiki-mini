# Security Policy

LLM Wiki Mini is local-first and does not require network access or API keys for its core CLI, tests, or evaluation harness.

## Supported versions

Security fixes target the current `main` branch until release channels are formalized.

## Reporting a vulnerability

Open a private advisory or contact the maintainer directly. Do not include live credentials or private source code in public issues.

## Secret handling

- Do not commit generated wiki/evaluation outputs that may contain copied project source.
- Do not commit `.env`, private keys, certificates, package build artifacts, or virtual environments.
- Use placeholders such as `[REDACTED]` or `your-api-key` in examples.
- The repository `.gitignore` excludes local env files, generated eval runs, virtualenvs, and build artifacts.

## Runtime posture

- Core commands operate on local files only.
- No telemetry is emitted by the package.
- If future integrations add remote LLM or judge APIs, keep credentials outside the repository and document the data sent to external services.
