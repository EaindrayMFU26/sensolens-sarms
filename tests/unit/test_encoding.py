"""Every text read, write and subprocess call names its encoding.

Without one, Python uses the platform's code page: cp1252 on most Windows machines. Git output, source files,
prompts and patches are UTF-8, so on Windows the draft step crashed on characters outside cp1252, git output
holding a byte cp1252 cannot decode came back as None, and the gate rejected patches whose context held
non-ASCII text. Linux and macOS default to UTF-8, so there only this check catches a regression.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUBPROCESS = {"run", "Popen", "check_output", "check_call", "call"}


def _missing(path):
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(n, ast.Call):
            continue
        kw = {k.arg: k.value for k in n.keywords}
        if "encoding" in kw or None in kw:
            continue
        f = n.func
        name = f.attr if isinstance(f, ast.Attribute) else f.id if isinstance(f, ast.Name) else None
        if name in ("read_text", "write_text"):
            yield n.lineno, name
        elif name == "open" and isinstance(f, ast.Name):
            mode = n.args[1] if len(n.args) > 1 else kw.get("mode")
            if mode is None or (isinstance(mode, ast.Constant) and "b" not in str(mode.value)):
                yield n.lineno, "open"
        elif name in SUBPROCESS and any(isinstance(kw.get(k), ast.Constant) and kw[k].value is True
                                        for k in ("text", "universal_newlines")):
            yield n.lineno, f"subprocess.{name}(text=True)"


def test_every_text_io_call_names_its_encoding():
    files = [*(ROOT / "src").rglob("*.py"), *(ROOT / "tools").glob("*.py"), *(ROOT / "tests").rglob("*.py")]
    bad = [f"{p.relative_to(ROOT).as_posix()}:{line} {what}" for p in files for line, what in _missing(p)]
    assert not bad, 'add encoding="utf-8" to:\n' + "\n".join(bad)


def test_the_check_sees_a_missing_encoding(tmp_path):
    p = tmp_path / "x.py"
    p.write_text('import subprocess\nopen("a")\nopen("b", "rb")\nsubprocess.run(["git"], text=True)\n'
                 'from pathlib import Path\nPath("c").write_text("x")\n', encoding="utf-8")
    assert [what for _, what in _missing(p)] == ["open", "subprocess.run(text=True)", "write_text"]
