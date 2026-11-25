"""import-linter records: find the configuration at a commit, read it with import-linter's own readers,
and normalise its contracts for the lint worker (shared by the replay, the rule compiler and the Differ).
"""
from __future__ import annotations

import os
import re
import tempfile
import tomllib

from sarms.core.git import git, show

# Files import-linter reads by default (its documentation: setup.cfg, .importlinter, pyproject.toml).
IL_FILES = [".importlinter", "setup.cfg", "pyproject.toml"]


def has_il_section(fname: str, text: str) -> bool:
    if fname.endswith(".toml"):
        try:
            return "importlinter" in tomllib.loads(text).get("tool", {})
        except Exception:
            return "[tool.importlinter" in text
    return re.search(r"^\[importlinter\]", text, re.M) is not None


def find_il_config(repo_dir, sha: str, files=IL_FILES):
    """(path, text) of the first file at `sha` that holds an import-linter section."""
    for f in files:
        t = show(repo_dir, sha, f)
        if t and has_il_section(f, t):
            return f, t
    return None, None


def find_il_configs_anywhere(repo_dir, sha: str, max_depth: int = 3):
    """[(path, text)] of every file at `sha`, up to max_depth folders deep, that holds an
    import-linter section (monorepos: api/pyproject.toml, libs/x/setup.cfg). Root first."""
    names = {".importlinter", "setup.cfg", "pyproject.toml"}
    out = []
    listing = git(repo_dir, "ls-tree", "-r", "--name-only", sha, check=False)
    for path in listing.splitlines():
        if path.rsplit("/", 1)[-1] in names and path.count("/") <= max_depth:
            t = show(repo_dir, sha, path)
            if t and has_il_section(path, t):
                out.append((path, t))
    out.sort(key=lambda pt: (pt[0].count("/"), pt[0]))
    return out


def read_il_options(fname: str, text: str):
    """Parse a config with import-linter's own readers, so we read exactly what lint-imports
    reads. Returns importlinter UserOptions or None. Tested with import-linter 2.15."""
    from importlinter import configuration
    configuration.configure()
    from importlinter.application import use_cases as uc
    suffix = ".toml" if fname.endswith(".toml") else ".ini"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=suffix, delete=False) as fh:
        fh.write(text)
        tmp = fh.name
    try:
        return uc.read_user_options(tmp)
    except Exception:
        return None
    finally:
        os.unlink(tmp)


def norm_ignore(entry: str) -> str:
    entry = entry.split("#")[0].strip().strip('"').strip("'").rstrip(",")
    return re.sub(r"\s*->\s*", " -> ", entry)


def as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [x.strip() for x in v.splitlines() if x.strip()]
    return list(v)


def optional_layers(layers):
    """Wrap every layer name in parentheses (import-linter's optional-layer syntax) so a contract
    can be checked at commits where some layers do not exist yet."""
    out = []
    for line in layers:
        parts = re.split(r"(\s*[|:]\s*)", str(line).strip())
        out.append("".join(p if re.fullmatch(r"\s*[|:]\s*", p) or p.startswith("(") or not p
                           else f"({p})" for p in parts))
    return out


def normalize_contracts(opts, strict: bool):
    """(session_options, contracts) ready for the lint worker. strict=True removes every
    ignore_imports entry (the strict record); layers are made optional either way; a contract
    without a name gets its id."""
    contracts = []
    for c in opts.contracts_options:
        c = dict(c)
        if strict:
            c.pop("ignore_imports", None)
        c["unmatched_ignore_imports_alerting"] = "none"
        if c.get("type") == "layers" and c.get("layers"):
            c["layers"] = optional_layers(as_list(c["layers"]))
        c.setdefault("name", c.get("id", "?"))
        contracts.append(c)
    session = dict(opts.session_options)
    if "root_packages" not in session:
        session["root_packages"] = [session.pop("root_package")]
    return session, contracts


def module_matches(pattern: str, module: str) -> bool:
    """Does `module` fall under `pattern`? A plain dotted name matches itself and its
    descendants (import-linter's reading of a contract module); `*` matches one dotted level
    and `**` any depth (rules.schema.yaml)."""
    pattern, module = pattern.strip(), module.strip()
    if "*" not in pattern:
        return module == pattern or module.startswith(pattern + ".")
    rx = "".join("[^.]+" if t == "*" else ".+" if t == "**" else re.escape(t)
                 for t in re.split(r"(\*\*|\*)", pattern) if t)
    return re.fullmatch(rx, module) is not None or re.fullmatch(rx + r"\..+", module) is not None
