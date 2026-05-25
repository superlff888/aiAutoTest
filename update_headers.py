#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch update file headers for all Python files under lee/"""

import os
import re
import glob

BASE_DIR = r"E:\AI\pythonProject\aiAutoTest"
LEE_DIR = os.path.join(BASE_DIR, "lee")

DEFAULT_CREATE_TIME = "2026/04/15 22:19"
DEFAULT_UPDATE_TIME = "2026/04/15 22:23"


def find_py_files(root_dir):
    """Find all .py files under root_dir, excluding __init__.py"""
    results = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for fname in filenames:
            if fname.endswith(".py") and fname != "__init__.py":
                results.append(os.path.join(dirpath, fname))
    results.sort()
    return results


def extract_header_info(content):
    """Extract @FilePath, @CreateTime, @UpdateTime from existing header."""
    filepath = None
    create_time = None
    update_time = None

    # Check @FilePath
    m = re.search(r'@FilePath\s*:\s*(.+)', content)
    if m:
        filepath = m.group(1).strip()

    # Check @CreateTime
    m = re.search(r'@CreateTime\s*:\s*(.+)', content)
    if m:
        create_time = m.group(1).strip()

    # Check @UpdateTime
    m = re.search(r'@UpdateTime\s*:\s*(.+)', content)
    if m:
        update_time = m.group(1).strip()

    return filepath, create_time, update_time


def find_header_end(lines):
    """Find the end line index (0-based) of the existing header comment block.
    The header starts with #!/usr/bin/env or # -*- coding or # @ or similar.
    It ends when we hit a non-comment, non-blank line or a different kind of content.
    Returns (start_idx, end_idx) or None if no header found.
    """
    header_start = None
    header_end = None

    # Patterns that indicate a header comment line
    header_patterns = [
        r'^\s*#!',                    # shebang
        r'^\s*#\s*-\*-',              # -*- coding
        r'^\s*#\s*@',                 # @FilePath, @Author etc.
        r'^\s*#\s*={3,}',            # ========
        r'^\s*#\s*-{3,}',            # --------
        r'^\s*#\s*$',                # just #
        r'^\s*#',                     # any comment
    ]

    # Find start: look for first comment-like line at top (after optional blank lines)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '':
            continue
        if stripped.startswith('#'):
            header_start = i
            break
        else:
            # First non-blank, non-comment line: no header
            return None

    if header_start is None:
        return None

    # Find end: consecutive comment lines + trailing blank lines
    # The header block ends when we hit a non-comment, non-blank line
    # But we also need to stop before a docstring (""")
    in_comment_block = True
    last_comment_line = header_start

    for i in range(header_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith('#'):
            last_comment_line = i
            in_comment_block = True
        elif stripped == '':
            # blank line - might be part of header spacing
            # Check if next non-blank line is still a comment
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and lines[j].strip().startswith('#'):
                last_comment_line = j
                i = j
            else:
                # End of header block
                in_comment_block = False
                # Check if there are blank lines between header and code
                # Include trailing blank lines up to 2
                blank_count = 0
                for k in range(i, min(i + 3, len(lines))):
                    if lines[k].strip() == '':
                        blank_count += 1
                    else:
                        break
                header_end = i + blank_count - 1
                break
        else:
            # Non-blank, non-comment line: header ended before this
            in_comment_block = False
            header_end = i - 1
            break

    if in_comment_block:
        header_end = len(lines) - 1

    return (header_start, header_end)


def generate_header(relative_path, create_time, update_time):
    """Generate the new header template."""
    return (
        "# !/usr/bin/env python3,# -*- coding: utf-8 -*-\n"
        "# --------------------------------------------\n"
        f"# @FilePath    : {relative_path}\n"
        "# @Author      : Lee大侠\n"
        "# @Desc        : 这是一个AI测试项目\n"
        f"# @CreateTime  : {create_time}\n"
        f"# @UpdateTime  : {update_time}\n"
        "# Copyright (c) 2026 Lee大侠. All rights reserved.\n"
        "# ========================================================\n"
    )


def process_file(filepath):
    """Process a single file. Returns True if modified, False otherwise."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract existing info
    existing_filepath, existing_create, existing_update = extract_header_info(content)

    create_time = existing_create if existing_create else DEFAULT_CREATE_TIME
    update_time = existing_update if existing_update else DEFAULT_UPDATE_TIME

    # Compute relative path from BASE_DIR
    rel_path = os.path.relpath(filepath, BASE_DIR).replace(os.sep, '\\')

    new_header = generate_header(rel_path, create_time, update_time)

    lines = content.split('\n')
    header_range = find_header_end(lines)

    if header_range is None:
        # No existing header - prepend new header
        if content.startswith('\n'):
            # Remove leading blank lines
            content = content.lstrip('\n')
        new_content = new_header + '\n\n' + content
    else:
        start_idx, end_idx = header_range
        # Replace lines from start_idx to end_idx (inclusive)
        before = '\n'.join(lines[:start_idx])
        after = '\n'.join(lines[end_idx + 1:])

        # Clean up leading/trailing blank lines
        if before.strip() == '':
            before = ''

        # Ensure proper spacing
        if after.startswith('\n'):
            after = after.lstrip('\n')

        new_content = new_header + '\n\n' + after

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main():
    files = find_py_files(LEE_DIR)
    print(f"Found {len(files)} Python files to process (excluding __init__.py)")

    modified = 0
    unchanged = 0
    errors = 0

    for filepath in files:
        try:
            if process_file(filepath):
                modified += 1
                print(f"  Modified: {os.path.relpath(filepath, BASE_DIR)}")
            else:
                unchanged += 1
        except Exception as e:
            errors += 1
            print(f"  Error: {os.path.relpath(filepath, BASE_DIR)} - {e}")

    print(f"\nResults:")
    print(f"  Total files: {len(files)}")
    print(f"  Modified: {modified}")
    print(f"  Unchanged (already correct): {unchanged}")
    print(f"  Errors: {errors}")


if __name__ == '__main__':
    main()
