import tomllib
from pathlib import Path


def test_pyproject_exposes_console_script_and_package_metadata():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    project = data["project"]
    assert project["name"] == "llm-wiki-mini"
    assert project["version"]
    assert project["readme"] == "README.md"
    assert "MIT" in project["license"]["text"]
    assert project["scripts"]["llm-wiki-mini"] == "llm_wiki_mini.cli:main"


def test_production_hygiene_files_exist():
    for required in [
        "README.md",
        "LICENSE",
        ".gitignore",
        ".github/workflows/ci.yml",
        "AGENTS.md",
        "docs/AGENT_USAGE.md",
    ]:
        assert Path(required).exists(), f"missing {required}"


def test_agent_first_contract_documents_no_install_usage():
    readme = Path("README.md").read_text(encoding="utf-8")
    agents = Path("AGENTS.md").read_text(encoding="utf-8")
    agent_usage = Path("docs/AGENT_USAGE.md").read_text(encoding="utf-8")
    combined = "\n".join([readme, agents, agent_usage])

    assert "Do not ask me to install anything" in combined
    assert "PYTHONPATH" in combined
    assert "python -m llm_wiki_mini.cli" in combined
    assert ".llm-wiki" in combined
    assert "https://github.com/doravidan/llm-wiki-mini" in combined
