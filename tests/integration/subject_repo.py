"""The tiny subject repository the end-to-end tests drive through real git.

app.ui, app.service and app.db under two import-linter contracts (CONFIG): the UI must not import the
database layer, and the service sits above the database. `make_subject` builds it with one clean commit
on main; `push` is a developer's push on top. Imported by the tests in this folder (pytest puts the
folder on sys.path), so no test module imports another.
"""
import subprocess
from pathlib import Path

CONFIG = """\
[importlinter]
root_package = app

[importlinter:contract:ui-db]
name = UI must not import the database layer
type = forbidden
source_modules = app.ui
forbidden_modules = app.db
allow_indirect_imports = True

[importlinter:contract:layers]
name = Service above DB
type = layers
layers =
    app.service
    app.db
"""

FILES = {
    ".importlinter": CONFIG,
    "app/__init__.py": "",
    "app/db.py": "def connect():\n    return 'db'\n",
    "app/service.py": "from app.db import connect\n\n\ndef run():\n    return connect()\n",
    "app/ui.py": "import os\n\n\ndef show():\n    return os.getcwd()\n",
}
TEST_FILE = {"tests/test_app.py": "from app.service import run\n\n\ndef test_run():\n    assert run() == 'db'\n"}


def g(repo, *a, author="Dev A"):
    return subprocess.run(["git", "-C", str(repo), "-c", f"user.name={author}", "-c", "user.email=dev@example.invalid", *a],
                          check=True, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def write(repo: Path, files: dict):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")


def push(repo, message, files: dict, author="Dev A"):
    """A developer's push: write files, commit on main. Returns the commit sha."""
    write(repo, files)
    g(repo, "add", "-A", author=author)
    g(repo, "commit", "-qm", message, author=author)
    return g(repo, "rev-parse", "HEAD", author=author).strip()


def make_subject(parent: Path, message="baseline", with_tests=True) -> Path:
    """<parent>/subject: the clean architecture as one commit on main (tests/test_app.py included unless with_tests=False)."""
    r = parent / "subject"
    write(r, {**FILES, **(TEST_FILE if with_tests else {})})
    g(r, "init", "-q", "-b", "main")
    push(r, message, {})
    return r
