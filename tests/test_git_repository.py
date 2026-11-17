import pytest
from git import Repo

from reviewai.tools.git_repository import GitRepositoryError, create_working_tree_diff


def test_gitpython_local_working_tree_diff(tmp_path):
    repo = Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "ReviewAI Test")
        config.set_value("user", "email", "reviewai@example.invalid")
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")
    repo.index.add([str(source)])
    repo.index.commit("initial")
    source.write_text("value = 2\n", encoding="utf-8")

    diff = create_working_tree_diff(tmp_path, "HEAD")
    assert "diff --git" in diff
    assert "+value = 2" in diff


def test_gitpython_rejects_revision_options(tmp_path):
    with pytest.raises(GitRepositoryError, match="Base ref"):
        create_working_tree_diff(tmp_path, "--upload-pack=bad")
