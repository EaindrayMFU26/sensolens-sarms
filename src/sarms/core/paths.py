"""Where sarms keeps things, and what a repository is called. Run every command from the sarms repository root.

  data/raw/REPO/          clones (git-ignored); REPO is the repository name without the owner
  data/raw/REPO.<kind>    worktrees beside a clone (wt = replay, draft, kernel, fi = fault injection)
  data/REPO/              derived files; data/REPO/rms/ is everything the product writes (git-ignored)
  reports/                generated reports
  docs/spec/              the frozen specification the code validates against (rule schema, ledger DDL)
"""
from __future__ import annotations

import os
import shutil
import stat
import sys
from pathlib import Path

DATA = Path("data")
RAW = DATA / "raw"
REPORTS = Path("reports")

# The sarms checkout itself (src/sarms/core/paths.py -> parents[3]). The spec lives there, not in the package:
# docs/spec is the frozen, hashed record that tools/validate_spec.py checks, and the code reads it in place.
REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "docs" / "spec"


def worktree_path(repo_dir, kind: str) -> Path:
    """<repo>.<kind> next to the clone (wt = replay, draft = the draft step, fi = fault injection).
    SARMS_WT_SUFFIX (e.g. "-linux") keeps separate worktrees when two operating systems share one
    clone through a mounted folder, since a worktree's .git file holds an absolute path."""
    return Path(f"{repo_dir}.{kind}{os.environ.get('SARMS_WT_SUFFIX', '')}")


def repo_name(owner_repo: str) -> str:
    """The repository's name without owner, host or folders: `kedro` for kedro-org/kedro, for any URL of it and for
    a checkout at C:/work/kedro. Clones (data/raw/<name>) and outputs (data/<name>/rms) are keyed on it, so every
    form of one repository lands in the same folders and none of them points outside data/."""
    value = str(owner_repo).strip()
    if is_git_url(value):
        value = value.split("?", 1)[0].split("#", 1)[0]
        value = value.replace(":", "/", 1) if value.startswith("git@") else value
        name = value.rstrip("/").split("/")[-1]
    else:
        name = Path(value).resolve().name if value else ""
    name = name[:-4] if name.lower().endswith(".git") else name
    if not name or name in (".", ".."):
        raise ValueError(f"no repository name in {owner_repo!r}")
    return name


def is_git_url(value: str) -> bool:
    value = str(value).strip()
    return "://" in value or value.startswith("git@")


def sarms_data_paths(repo: str | os.PathLike[str]) -> list[Path]:
    """Return only SARMS-owned clone, worktree, and result paths for a repository."""
    name = repo_name(str(repo))
    raw = RAW / name
    return [
        raw,
        Path(f"{raw}.wt"),
        Path(f"{raw}.draft"),
        Path(f"{raw}.kernel"),
        Path(f"{raw}.fi"),
        Path(f"{raw}.ilcache"),
        DATA / name / "rms",
    ]


def rms_dir(repo, out=None) -> Path:
    """Where the product writes for one repository: `out` when given, else data/<repo>/rms."""
    return Path(out) if out else DATA / repo_name(str(repo)) / "rms"


def remove_tree(path) -> None:
    """shutil.rmtree that also removes read-only files. Git marks its object files read-only, and on Windows a plain
    rmtree (or one with ignore_errors=True, which then leaves the folder behind) cannot delete them."""
    def unlock_and_retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE | stat.S_IREAD)
        func(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=unlock_and_retry)
    else:  # Python 3.11: onexc does not exist yet
        shutil.rmtree(path, onerror=unlock_and_retry)
