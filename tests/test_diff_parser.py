import pytest

from reviewai.tools.diff_parser import parse_git_diff


SINGLE_FILE_DIFF = """diff --git a/src/example.py b/src/example.py
index 1111111..2222222 100644
--- a/src/example.py
+++ b/src/example.py
@@ -1,3 +1,3 @@
 before = 1
-old_value = 2
+new_value = 2
 after = 3
"""


def test_parse_added_and_deleted_lines_and_paths():
    parsed = parse_git_diff(SINGLE_FILE_DIFF)
    assert parsed.additions == 1
    assert parsed.deletions == 1
    assert parsed.files[0].display_path == "src/example.py"
    assert [(line.change_type, line.line_number, line.content) for line in parsed.files[0].changed_lines] == [
        ("deleted", 2, "old_value = 2"),
        ("added", 2, "new_value = 2"),
    ]


def test_parse_multiple_files_without_merging_hunks():
    diff = SINGLE_FILE_DIFF + SINGLE_FILE_DIFF.replace("example.py", "second.py")
    parsed = parse_git_diff(diff)
    assert len(parsed.files) == 2
    assert [file.display_path for file in parsed.files] == ["src/example.py", "src/second.py"]


def test_parse_standard_unprefixed_multiple_file_diff():
    one_file = "--- " + SINGLE_FILE_DIFF.split("\n--- ", 1)[1]
    parsed = parse_git_diff(one_file + "\n" + one_file.replace("example.py", "second.py"))
    assert len(parsed.files) == 2
    assert parsed.additions == 2


def test_empty_diff_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        parse_git_diff("  \n")


def test_non_diff_text_is_rejected():
    with pytest.raises(ValueError, match="unified Git diff"):
        parse_git_diff("print('hello')")


def test_malformed_hunk_is_rejected():
    diff = SINGLE_FILE_DIFF.replace("@@ -1,3 +1,3 @@", "@@ broken @@")
    with pytest.raises(ValueError, match="Malformed unified diff hunk"):
        parse_git_diff(diff)


def test_hunk_line_count_mismatch_is_rejected():
    diff = SINGLE_FILE_DIFF.replace("@@ -1,3 +1,3 @@", "@@ -1,8 +1,8 @@")
    with pytest.raises(ValueError, match="line counts"):
        parse_git_diff(diff)


def test_added_lines_starting_with_plus_are_preserved():
    diff = SINGLE_FILE_DIFF.replace("+new_value = 2", "+++new_value = 2")
    parsed = parse_git_diff(diff)
    assert parsed.files[0].changed_lines[-1].content == "++new_value = 2"
