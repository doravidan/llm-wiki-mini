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
    for required in ["README.md", "LICENSE", ".gitignore", ".github/workflows/ci.yml"]:
        assert Path(required).exists(), f"missing {required}"
