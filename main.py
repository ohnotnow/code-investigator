# from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from agents import Agent, Runner, function_tool
import re
import os

class FileSummary(BaseModel):
    files: list[str]
    implementation_summary: str


@function_tool
def list_files(directory: str, recursive: bool) -> str:
    """List all files in a directory."""
    print(f"Listing files in {directory} {'recursively' if recursive else ''}")
    file_list = ""
    if recursive:
        files = []
        # We only want to list regular files and directories - ignore dotfiles
        for root, dirs, current_files in os.walk(directory):
            # Filter out dot directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            # Filter out dot files and add to our list
            for current_file in current_files:
                if not current_file.startswith('.'):
                    files.append(os.path.join(root, current_file))
        # Remove duplicates and sort for consistent output
        files = sorted(set(files))
        file_list = "\n".join(files)
    else:
        try:
            files = []
            for file in os.listdir(directory):
                if not file.startswith("."):
                    files.append(os.path.join(directory, file))
            file_list = "\n".join(files)
        except FileNotFoundError:
            file_list = f"Directory not found: {directory}"
    return file_list

@function_tool
def cat_file(file_path: str) -> str:
    """Read a file and return the contents."""
    print(f"Reading {file_path}")
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"

@function_tool
def grep_file(file_path: str, python_regex_pattern: str, include_before_lines: int, include_after_lines: int) -> str:
    """Search for a python re.searchpattern in a file and return the lines around the match."""
    if not include_before_lines:
        include_before_lines = 0
    if not include_after_lines:
        include_after_lines = 0
    print(f"Searching for {python_regex_pattern} in {file_path} with {include_before_lines} before and {include_after_lines} after")
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

if __name__ == "__main__":
    agent = Agent(
        name="Codebase Agent",
        model="gpt-4.1",
        tools=[list_files, cat_file, grep_file],
        instructions="""
            You're a helpful assistant who is tasked with reading a users feature request and finding the most relevant
            files in the codebase which will be used to implement the new feature.

            You should use the following tools to help you:
            - list_files: List all files in a directory.
            - cat_file: Read a file and return the whole contents.
            - grep_file: Search for a pattern in a file using pythons re.searchand return the lines around the match.

            You should always use the list_files tool to get a list of files in the codebase first then use the other tools
            to find the most relevant files.  This will also help you understand the type of codebase or framework it is.

            **Do not try to list files or directories that don't exist.**

            Once you have found the relevant files to your satisfaction, you should write a summary of the changes you suggest to implement the feature and what - if any - files to update.
            You do not need to give the full implementation, just a summary of the changes so the user can implement it themselves.
        """,
    )

    print("Starting...")
    result = Runner.run_sync(agent, input="Could we add an rm_file tool to the codebase and make it available to the agent?")
    print(result.final_output)
