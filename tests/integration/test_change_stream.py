"""The change stream survives a dropped connection, and says why when it cannot.

ramses_rf's mining died after 44 minutes: its clone is partial (--filter=blob:none), so `git log --numstat` fetched
file versions on demand, one DNS lookup failed, git exited 128, and the error that reached the user had no git
message in it. Here the "network" is a file:// origin that is moved away and back.
"""
import subprocess

import pytest
from subject_repo import g

from sarms.mining.gitlog import stream


@pytest.fixture
def partial_clone(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    g(origin, "init", "-q", "-b", "main")
    g(origin, "config", "uploadpack.allowFilter", "true")
    g(origin, "config", "uploadpack.allowAnySHA1InWant", "true")
    for i in range(3):
        (origin / "app").mkdir(exist_ok=True)
        (origin / "app" / "core.py").write_text("".join(f"x{j} = {j}\n" for j in range(i + 1)), encoding="utf-8")
        g(origin, "add", "-A")
        g(origin, "commit", "-qm", f"change {i}")
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", origin.as_uri(), str(clone)],
                   check=True, capture_output=True)
    return origin, clone


def test_a_dropped_connection_is_retried_and_the_stream_completes(partial_clone, tmp_path):
    origin, clone = partial_clone
    away = tmp_path / "origin-away"
    origin.rename(away)                                    # the network drops
    said = []

    def log(s):
        said.append(s)
        away.rename(origin)                                # ... and is back before the retry

    rows = list(stream(clone, waits=(0, 0), log=log))
    assert len(said) == 1 and "retry 1 of 2" in said[0]
    assert len(rows) == 3 and [f[1] for r in rows for f in r["files"]] == [1, 1, 1]


def test_when_retries_run_out_the_error_carries_gits_message(partial_clone, tmp_path):
    origin, clone = partial_clone
    origin.rename(tmp_path / "origin-away")
    said = []
    with pytest.raises(RuntimeError, match="promisor remote"):
        list(stream(clone, waits=(0, 0), log=said.append))
    assert len(said) == 2


def test_an_error_that_is_not_the_network_is_not_retried(tmp_path):
    said = []
    with pytest.raises(RuntimeError, match="not a git repository"):
        list(stream(tmp_path, waits=(0, 0), log=said.append))
    assert said == []
