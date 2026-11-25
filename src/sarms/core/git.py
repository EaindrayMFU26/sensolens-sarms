"""Git as a subprocess: clones, refs, the first-parent chain, file contents at a commit, patch fingerprints.

History is always the first-parent chain of the default branch, so every merge commit is
read as its diff against parents[0]: what that push added to the branch.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from sarms.core.paths import RAW, is_git_url, repo_name


def run(args, cwd=None, check=True) -> str:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, args))}\n{p.stderr.strip()}")
    return p.stdout


def git(repo_dir, *args, check=True) -> str:
    return run(["git", "-C", str(repo_dir), *args], check=check)


def ensure_clone(owner_repo: str, checkout: bool = True) -> Path:
    """data/raw/REPO as a partial clone (--filter=blob:none): all commits and trees, file
    contents fetched only when something reads them."""
    d = RAW / repo_name(owner_repo)
    if d.exists():
        # a failed clone can leave a folder with a broken .git; git would then silently walk UP to the
        # parent repository (sarms itself), so make sure d is the top of its own repository first
        top = subprocess.run(["git", "-C", str(d), "rev-parse", "--show-toplevel"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
        if top and Path(top).resolve() == d.resolve():
            git(d, "fetch", "-q", "origin")
            return d
        import shutil  # noqa: PLC0415
        shutil.rmtree(d, ignore_errors=True)
    RAW.mkdir(parents=True, exist_ok=True)
    url = str(owner_repo).strip()
    if not is_git_url(url):
        url = f"https://github.com/{url}.git"
    args = ["git", "clone", "-q", "--filter=blob:none"] + ([] if checkout else ["--no-checkout"])
    run(args + [url, str(d)])
    return d


def resolve_repo_input(repo: str | os.PathLike[str]) -> Path:
    """Resolve a local path or Git URL to a local checkout."""
    value = str(repo).strip()
    if not is_git_url(value):
        return Path(value).resolve()
    return ensure_clone(value)


def resolve_ref(repo_dir, branch: str | None = None) -> str:
    """origin/<branch> if it exists (fresh after a fetch), else the branch; default branch if None."""
    if not branch:
        ref = git(repo_dir, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", check=False).strip()
        if not ref:
            git(repo_dir, "remote", "set-head", "origin", "--auto", check=False)
            ref = git(repo_dir, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD", check=False).strip()
        if not ref:  # no remote (a local repository, the Term 2 CI checkout): the current branch
            ref = git(repo_dir, "symbolic-ref", "-q", "--short", "HEAD", check=False).strip() or "HEAD"
        return ref
    if git(repo_dir, "rev-parse", "-q", "--verify", f"origin/{branch}", check=False).strip():
        return f"origin/{branch}"
    return branch


def first_parent(repo_dir, ref: str, since: str | None = None):
    """[(idx, sha, committer_iso, subject)] oldest -> newest; idx = position on the full chain."""
    # -z: NUL between records, because a subject line can hold characters str.splitlines() treats
    # as line breaks (PostHog has a subject with U+001D), which split a record in two.
    out = git(repo_dir, "log", "-z", "--first-parent", "--reverse", "--format=%H%x1f%cI%x1f%s", ref)
    rows = []
    for idx, rec in enumerate(r for r in out.split("\0") if r):
        sha, ts, subj = rec.split("\x1f", 2)
        rows.append((idx, sha, ts, subj.replace("\n", " ")))
    if since:
        rows = [r for r in rows if r[2][:10] >= since]
    return rows


def show(repo_dir, sha: str, path: str):
    p = subprocess.run(["git", "-C", str(repo_dir), "show", f"{sha}:{path}"], capture_output=True)
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else None


def patch_fingerprint(patch: str) -> frozenset:
    """What a unified diff changes, as a set of (file, '+' or '-', stripped line). Two patches with the same
    fingerprint make the same change, whatever their context lines, hunk offsets or whitespace."""
    out, path = set(), None
    for ln in patch.splitlines():
        if ln.startswith("+++ "):
            path = ln[4:].strip()
            path = None if path == "/dev/null" else re.sub(r"^b/", "", path)
        elif ln.startswith("--- "):
            continue
        elif ln[:1] in "+-" and path and ln[1:].strip():
            out.add((path, ln[0], ln[1:].strip()))
    return frozenset(out)
