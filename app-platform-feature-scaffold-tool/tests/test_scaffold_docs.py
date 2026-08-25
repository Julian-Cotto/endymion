from pathlib import Path


def test_scaffold_docs_exist() -> None:
    root = Path(__file__).parent.parent

    assert (root / "docs" / "registry-contract.md").exists()
    assert (root / "docs" / "shell-consumption-contract.md").exists()