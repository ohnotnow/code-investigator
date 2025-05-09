"""
This module contains tools for file operations.
"""

import re
from pathlib import Path
import subprocess
from agents import function_tool
from utils.file_utils import (
    filename_unsafe,
    is_a_valid_file,
    is_a_valid_directory,
    count_files
)
from helpers.project_type import ProjectTypeAgent


@function_tool
def get_project_structure() -> str:
    """
    Get the project structure of the codebase.
    Returns :
    - the root directory
    - a list of non-hidden files in the root directory
    - a list of non-hidden directories in the root
    - a list of non-hidden directories in the all of the codebase
    - a guess at the language and framework used

    The output should follow this format:
    .
    - file1.py
    - readme.md
    - dir1/ (10 files)
        - dir5/ (7 files)
          - dir6/ (2 files)
          - dir7/ (5 files)
    - dir2/ (10 files)
        - dir3 (1 file)
        - dir4 (2 files)

    ## Estimated project type : PHP / Laravel
    """
    def list_dir_tree(path, indent):
        entries = []
        total_files = 0
        try:
            items = sorted([p for p in Path(path).iterdir()])
        except FileNotFoundError:
            return []
        for item in items:
            if item.name.startswith('.'):
                continue  # skip hidden files/dirs
            if item.name in ['node_modules', 'vendor', 'dist', 'storage', 'build', 'public', 'cache', 'logs']:
                continue
            if item.is_dir():
                file_count = len([f for f in item.iterdir() if not f.name.startswith('.')])
                total_files += file_count
                entries.append('  ' * indent + f'- {item.name}/ ({file_count} {'file' if file_count == 1 else 'files'})')
                entries.extend(list_dir_tree(item, indent + 1))
            else:
                if indent == 0:
                    entries.append('  ' * indent + f'- {item.name}')
        return entries

    print("- Getting project structure...")
    structure = list_dir_tree('.', 0)
    project_type = ProjectTypeAgent('.').run()
    project_info = f"\n\n## Estimated project type : {project_type.language} / {project_type.framework}\n\n"
    output = '\n'.join(structure)
    output += project_info
    total_files = count_files(output)
    output += f"\n\n## Total files: {total_files}\n\n"
    return output


@function_tool
def list_files(directory: str, recursive: bool) -> str:
    """List all files in a directory."""
    print(f"- Listing files in {directory} {'recursively' if recursive else ''}")
    if filename_unsafe(directory):
        return "Forbidden"
    if not is_a_valid_directory(directory):
        return f"Not a valid directory: {directory}"
    file_list = ""
    if recursive:
        files = []
        for p in Path(directory).rglob("*"):
            if not any(part.startswith('.') for part in p.parts) and not any(part in ['node_modules', 'vendor', 'dist', 'build', 'public'] for part in p.parts):
                if p.is_file():
                    files.append(str(p))
                else:
                    files.append(str(p) + "/")
        files = sorted(set(files))
        file_list = "\n".join(files)
    else:
        try:
            files = []
            for file in Path(directory).iterdir():
                if not file.name.startswith("."):
                    if file.is_file():
                        files.append(str(file))
                    else:
                        files.append(str(file) + "/")
            file_list = "\n".join(files)
        except FileNotFoundError:
            file_list = f"Directory not found: {directory}"
    return file_list


@function_tool
def cat_file(file_path: str) -> str:
    """Read a file and return the contents."""
    if filename_unsafe(file_path):
        return "Forbidden"
    if not is_a_valid_file(file_path):
        return f"Not a valid file: {file_path}"
    print(f"- Reading {file_path}")
    if "readme" in file_path.lower():
        # sometimes the LLM is 'lazy' and just reads the readme file.  So prevent it being useful.
        print(f"  - Faking readme file: {file_path}")
        return "# README\n\n- TODO\n\n"
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"


@function_tool
def grep_file(file_path: str, python_regex_pattern: str, include_before_lines: int, include_after_lines: int) -> str:
    """Search for a python re.search pattern in a single file (no recursion or directory listing) and return the lines around the match."""
    if filename_unsafe(file_path):
        return "Forbidden"
    if not is_a_valid_file(file_path):
        return f"Not a valid file: {file_path}"
    if not include_before_lines:
        include_before_lines = 0
    if not include_after_lines:
        include_after_lines = 0
    print(f"- Searching for {python_regex_pattern} in {file_path} with {include_before_lines} before and {include_after_lines} after")
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            matches = []
            for i, line in enumerate(lines):
                # use regex to find the pattern
                if re.search(python_regex_pattern, line):
                    # Calculate start and end indices for context
                    start_idx = max(0, i - include_before_lines)
                    end_idx = min(len(lines), i + include_after_lines + 1)

                    # Add context lines before the match
                    for j in range(start_idx, i):
                        matches.append(f"Line: {j+1} - {lines[j]}")

                    # Add the matching line
                    matches.append(f"Line: {i+1} - {line}")

                    # Add context lines after the match
                    for j in range(i + 1, end_idx):
                        matches.append(f"Line: {j+1} - {lines[j]}")

                    # Add a separator between different matches
                    if end_idx < len(lines):
                        matches.append("---")

            return "\n".join(matches)
    except FileNotFoundError:
        return f"File not found: {file_path}"


@function_tool
def get_git_remotes() -> str:
    """Get the git remotes for the codebase."""
    print(f"- Getting git remotes")
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, cwd='.')
    return result.stdout


@function_tool
def write_report(files: list[str], implementation_summary: str) -> str:
    """Write a report of the changes to the codebase."""
    return "The report is as follows: " + implementation_summary
