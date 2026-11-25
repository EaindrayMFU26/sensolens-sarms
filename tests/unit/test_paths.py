"""Every form of one repository maps to the same folders under data/, and those folders can always be deleted.

tools/product_batch.py clones owner/name and then runs `sarms auto <url>`. When repo_name kept the owner, that made
two clones, put the batch's report lookup in the wrong folder, and for sqlfluff/sqlfluff made sarms delete the
batch's clone, which failed on Windows because git's read-only pack files survived rmtree(ignore_errors=True).
"""
import stat
from pathlib import Path

import pytest

from sarms.core.paths import DATA, RAW, remove_tree, repo_name, rms_dir, sarms_data_paths

FORMS = ["kedro-org/kedro", "kedro-org/kedro.git", "https://github.com/kedro-org/kedro.git",
         "https://github.com/kedro-org/kedro/", "git@github.com:kedro-org/kedro.git", "kedro", str(Path("work") / "kedro")]


@pytest.mark.parametrize("given", FORMS)
def test_every_form_of_a_repository_has_one_name(given):
    assert repo_name(given) == "kedro"


def test_owner_name_and_its_url_share_the_clone_and_the_outputs():
    a = sarms_data_paths("sqlfluff/sqlfluff")
    assert a == sarms_data_paths("https://github.com/sqlfluff/sqlfluff.git")
    assert a[0] == RAW / "sqlfluff" and a[-1] == DATA / "sqlfluff" / "rms"
    assert rms_dir("https://github.com/sqlfluff/sqlfluff.git") == DATA / "sqlfluff" / "rms"


def test_a_local_checkout_never_maps_outside_data(tmp_path):
    """`sarms clean <path> --yes` deletes sarms_data_paths(path): SARMS's own folders, never the checkout itself."""
    paths = sarms_data_paths(str(tmp_path / "proj"))
    assert all(not p.is_absolute() and p.parts[0] == "data" for p in paths)
    assert paths[0] == RAW / "proj" and paths[-1] == DATA / "proj" / "rms"


@pytest.mark.parametrize("given", ["", "/"])
def test_an_input_without_a_name_is_refused(given):
    with pytest.raises(ValueError):
        repo_name(given)


def test_remove_tree_deletes_read_only_files(tmp_path):
    pack = tmp_path / "clone" / ".git" / "objects" / "pack"
    pack.mkdir(parents=True)
    for name in ("pack-1.pack", "pack-1.idx"):
        (pack / name).write_bytes(b"x")
        (pack / name).chmod(stat.S_IREAD)
    remove_tree(tmp_path / "clone")
    assert not (tmp_path / "clone").exists()
