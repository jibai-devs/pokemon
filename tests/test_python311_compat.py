"""Guard the files bundled for Kaggle against syntax newer than Python 3.11."""

import ast
from pathlib import Path


def test_submission_has_python311_syntax() -> None:
    root = Path(__file__).parents[1]
    paths = [root / "main.py", *(root / "src" / "pokemon").glob("*.py")]

    for path in paths:
        ast.parse(path.read_text(), filename=str(path), feature_version=(3, 11))
