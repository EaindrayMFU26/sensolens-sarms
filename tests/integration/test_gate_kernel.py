"""Gate G0-G8 and the kernel on the tiny repository: an accepted record lands as a sensolens-sarms commit that reverts
in one step; a draft that touches a test fails G0; a tampered record is refused."""
import json
import textwrap

import pytest
from subject_repo import g, make_subject, push


@pytest.fixture
def repo(tmp_path):
    return make_subject(tmp_path)


def test_gate_accepts_a_real_fix_and_the_kernel_lands_it(repo, tmp_path):
    from sarms.kernel.apply import apply_decision, developer_reverts, revert_own_commit
    from sarms.ledger.hypergraph import Ledger
    from sarms.rules.compile import compile_repo
    from sarms.synthesize.draft import draft_one
    from sarms.verify.gate import run_gate, verify_signature

    rms = tmp_path / "rms"
    rules_dir = rms / "rules"
    compile_repo(repo, out_dir=rules_dir, repo_label="app")
    sha = push(repo, "feature: ui reads db", {
        "app/ui.py": "import os\nfrom app.db import connect\n\n\ndef show():\n    return os.getcwd() + connect()\n",
        "tests/test_ui.py": "from app.ui import show\n\n\ndef test_show():\n    assert show().endswith('db')\n"})
    replies = tmp_path / "replies"
    replies.mkdir()
    (replies / "1.txt").write_text(textwrap.dedent("""\
        FILE: app/ui.py
        <<<<<<< FIND
        from app.db import connect
        =======
        from app.service import run as connect
        >>>>>>> REPLACE
        REASON: reach the database through the service layer
        """), encoding="utf-8")
    result, d = draft_one(repo, rules_dir=rules_dir, rms_dir=rms, base_url=f"fake:{replies}",
                          tests="python -m pytest -q -p no:cacheprovider tests", log=lambda s: None)
    assert result["verdict"] == "draft_passes"
    record, path = run_gate(repo, sha, rules_dir, d, rms, tests="python -m pytest -q -p no:cacheprovider", log=lambda s: None)
    assert record["verdict"] == "accept", [(x["line"], x["pass"], x["evidence"]) for x in record["gate"]]
    assert [x["pass"] for x in record["gate"]] == [True] * 9
    from sarms.verify.gate import _salt
    assert verify_signature(record, _salt(repo))
    led = Ledger(rms / "sthg")
    fix = apply_decision(repo, path, d, ledger=led, log=lambda s: None)
    assert fix and g(repo, "log", "-1", "--format=%an", fix).strip() == "sensolens-sarms"
    assert g(repo, "rev-parse", "sarms/fixes").strip() == fix
    assert "Decision record" in g(repo, "log", "-1", "--format=%b", fix)
    assert json.loads(path.read_text(encoding="utf-8"))["applied_commit"] == fix
    assert g(repo, "status", "--short").strip() == ""                      # the developer's checkout untouched
    # the developer's view: main still has the violation; the fix is one revert away on its branch
    g(repo, "checkout", "-q", "sarms/fixes")
    new = revert_own_commit(repo, fix, ledger=led, log=lambda s: None)
    assert g(repo, "diff", sha, "--", ".").strip() == ""
    assert developer_reverts(repo) == [(new, fix)]
    acts = led.actions()
    assert list(acts.kind) == ["apply", "revert_seen"]


def test_gate_stops_at_g0_when_the_draft_edits_a_test_and_refuses_tampering(repo, tmp_path):
    from sarms.kernel.apply import apply_decision
    from sarms.rules.compile import compile_repo
    from sarms.verify.gate import run_gate

    rms = tmp_path / "rms"
    rules_dir = rms / "rules"
    compile_repo(repo, out_dir=rules_dir, repo_label="app")
    sha = push(repo, "feature", {"app/ui.py": "from app.db import connect\n\n\ndef show():\n    return connect()\n"})
    d = rms / "drafts" / "fake"
    d.mkdir(parents=True)
    (d / "result.json").write_text(json.dumps({"sha": sha, "class": "llm_draft", "prompt_hash": "x",
                                               "violation": {"rule_id": "R-app-UI-must-not-import-the-database-layer-1", "contract": "c", "edge_from": "app.ui", "edge_to": "app.db"}}), encoding="utf-8")
    (d / "patch.diff").write_text(textwrap.dedent("""\
        diff --git a/tests/test_app.py b/tests/test_app.py
        --- a/tests/test_app.py
        +++ b/tests/test_app.py
        @@ -1,5 +1,5 @@
         from app.service import run


         def test_run():
        -    assert run() == 'db'
        +    assert True
        """), encoding="utf-8")
    record, path = run_gate(repo, sha, rules_dir, d, rms, tests="python -m pytest -q -p no:cacheprovider", log=lambda s: None)
    assert record["verdict"] == "escalate" and record["stopped_at"] == "G0"
    assert [x["pass"] for x in record["gate"]] == [False] + [None] * 8
    assert apply_decision(repo, path, d, log=lambda s: None) is None
    rec = json.loads(path.read_text(encoding="utf-8"))
    rec["verdict"] = "accept"
    path.write_text(json.dumps(rec), encoding="utf-8")
    with pytest.raises(PermissionError):
        apply_decision(repo, path, d, log=lambda s: None)


@pytest.mark.parametrize("comment", ["# café", "# a → b", "# \U0001f41b fixed"], ids=["latin", "arrow", "emoji"])
def test_a_fix_next_to_non_ascii_text_lands_intact(repo, tmp_path, comment):
    """Windows regression: with the cp1252 default, the prompt write crashed on the arrow and the emoji, and
    decoding git output as UTF-8 while patch files stayed cp1252 made the gate reject the latin patch (G0)."""
    from sarms.kernel.apply import apply_decision
    from sarms.ledger.hypergraph import Ledger
    from sarms.rules.compile import compile_repo
    from sarms.synthesize.draft import draft_one
    from sarms.verify.gate import run_gate

    rms = tmp_path / "rms"
    rules_dir = rms / "rules"
    compile_repo(repo, out_dir=rules_dir, repo_label="app")
    sha = push(repo, "feature: ui reads db", {
        "app/ui.py": f"import os\n{comment}\nfrom app.db import connect\n\n\ndef show():\n    return os.getcwd() + connect()\n",
        "tests/test_ui.py": "from app.ui import show\n\n\ndef test_show():\n    assert show().endswith('db')\n"})
    replies = tmp_path / "replies"
    replies.mkdir()
    (replies / "1.txt").write_text("FILE: app/ui.py\n<<<<<<< FIND\nfrom app.db import connect\n=======\n"
                                   "from app.service import run as connect\n>>>>>>> REPLACE\nREASON: go through the service\n",
                                   encoding="utf-8")
    result, d = draft_one(repo, rules_dir=rules_dir, rms_dir=rms, base_url=f"fake:{replies}",
                          tests="python -m pytest -q -p no:cacheprovider tests", log=lambda s: None)
    assert result["verdict"] == "draft_passes"
    record, path = run_gate(repo, sha, rules_dir, d, rms, tests="python -m pytest -q -p no:cacheprovider", log=lambda s: None)
    assert record["verdict"] == "accept", [(x["line"], x["pass"], x["evidence"]) for x in record["gate"]]
    fix = apply_decision(repo, path, d, ledger=Ledger(rms / "sthg"), log=lambda s: None)
    landed = g(repo, "show", f"{fix}:app/ui.py")
    assert comment in landed and "from app.service import run as connect" in landed
