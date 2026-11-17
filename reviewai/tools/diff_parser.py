"""Parse unified Git patches without applying or executing submitted code."""

import re

from reviewai.core.schemas import ChangedLine, FileChange, ParsedDiff
from reviewai.utils.validators import validate_diff_text, validate_parsed_diff

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _header_path(value: str) -> str | None:
    value = value.strip()
    if value == "/dev/null":
        return None
    if value.startswith('"'):
        # Git's quoted header is uncommon; retain a safe visible name rather than
        # attempting shell-style decoding on untrusted input.
        value = value.strip('"')
    return value.split("\t", 1)[0].removeprefix("a/").removeprefix("b/")


def parse_git_diff(diff_text: str, source: str = "diff") -> ParsedDiff:
    """Return files and changed lines from a valid unified diff."""
    validate_diff_text(diff_text)
    lines = diff_text.splitlines()
    files: list[FileChange] = []
    index = 0
    while index < len(lines):
        if not lines[index].startswith("diff --git ") and not (
            lines[index].startswith("--- ") and index + 1 < len(lines) and lines[index + 1].startswith("+++ ")
        ):
            index += 1
            continue

        file_start = index
        old_path: str | None = None
        new_path: str | None = None
        status = "modified"
        if lines[index].startswith("diff --git "):
            header = lines[index][len("diff --git "):]
            # Git path headers are separated into two paths; paths with spaces may be quoted.
            if header.startswith('"'):
                match = re.match(r'^"(.+)"\s+"(.+)"$', header)
                if match:
                    old_path, new_path = _header_path(match.group(1)), _header_path(match.group(2))
            else:
                parts = header.split(" ", 1)
                if len(parts) == 2:
                    old_path, new_path = _header_path(parts[0]), _header_path(parts[1])
            index += 1

        while (
            index < len(lines)
            and not lines[index].startswith("@@ ")
            and not lines[index].startswith("diff --git ")
        ):
            line = lines[index]
            if line.startswith("new file mode"):
                status = "added"
            elif line.startswith("deleted file mode"):
                status = "deleted"
            elif line.startswith("rename from "):
                old_path = line[len("rename from "):]
                status = "renamed"
            elif line.startswith("rename to "):
                new_path = line[len("rename to "):]
                status = "renamed"
            elif line.startswith("--- "):
                old_path = _header_path(line[4:])
                if old_path is None:
                    status = "added"
            elif line.startswith("+++ "):
                new_path = _header_path(line[4:])
                if new_path is None:
                    status = "deleted"
            index += 1

        changed_lines: list[ChangedLine] = []
        additions = deletions = 0
        in_hunk = False
        old_line = new_line = 0
        old_remaining: int | None = None
        new_remaining: int | None = None
        while (
            index < len(lines)
            and not lines[index].startswith("diff --git ")
            and not (
                old_remaining == 0
                and new_remaining == 0
                and lines[index].startswith("--- ")
                and index + 1 < len(lines)
                and lines[index + 1].startswith("+++ ")
            )
        ):
            line = lines[index]
            if line.startswith("@@ "):
                if old_remaining not in (None, 0) or new_remaining not in (None, 0):
                    raise ValueError("Unified diff hunk line counts do not match the hunk header.")
                match = _HUNK_RE.match(line)
                if not match:
                    raise ValueError(f"Malformed unified diff hunk header: {line[:120]}")
                old_line = int(match.group(1))
                new_line = int(match.group(3))
                old_remaining = int(match.group(2)) if match.group(2) is not None else 1
                new_remaining = int(match.group(4)) if match.group(4) is not None else 1
                in_hunk = True
            elif in_hunk and line.startswith("+"):
                additions += 1
                changed_lines.append(ChangedLine(line_number=max(new_line, 1), content=line[1:], change_type="added"))
                new_line += 1
                new_remaining -= 1
            elif in_hunk and line.startswith("-"):
                deletions += 1
                changed_lines.append(ChangedLine(line_number=max(old_line, 1), content=line[1:], change_type="deleted"))
                old_line += 1
                old_remaining -= 1
            elif in_hunk and line.startswith(" "):
                old_line += 1
                new_line += 1
                old_remaining -= 1
                new_remaining -= 1
            elif in_hunk and line.startswith("\\ No newline"):
                pass
            elif in_hunk and line and line[0] not in "+- ":
                raise ValueError(f"Unexpected line in unified diff hunk: {line[:120]}")
            if (old_remaining is not None and old_remaining < 0) or (
                new_remaining is not None and new_remaining < 0
            ):
                raise ValueError("Unified diff hunk contains more lines than declared in its header.")
            index += 1

        if old_remaining not in (None, 0) or new_remaining not in (None, 0):
            raise ValueError("Unified diff hunk line counts do not match the hunk header.")

        if old_path is None and new_path is None:
            # Fallback to the diff --git header's right-hand path where possible.
            if file_start < len(lines) and lines[file_start].startswith("diff --git "):
                name = lines[file_start][len("diff --git "):].split(" ")[-1]
                new_path = _header_path(name)
        patch = "\n".join(lines[file_start:index])
        files.append(FileChange(
            old_path=old_path,
            new_path=new_path,
            status=status,
            additions=additions,
            deletions=deletions,
            changed_lines=changed_lines,
            patch=patch,
        ))

    if not files:
        raise ValueError("No file changes were found in the unified diff.")
    parsed = ParsedDiff(
        files=files,
        additions=sum(file.additions for file in files),
        deletions=sum(file.deletions for file in files),
        source=source,
    )
    return validate_parsed_diff(parsed)
