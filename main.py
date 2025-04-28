# from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from agents import Agent, Runner, function_tool
import re
import os
from sys import argv
class FileSummary(BaseModel):
    files: list[str]
    implementation_summary: str

@function_tool
def get_project_structure() -> str:
    """
    Get the project structure of the codebase.
    Returns :
    - the root directory
    - a list of non-hidden files in the root directory
    - a list of non-hidden directories in the root
    - a list of non-hidden directories in the all of the codebase

    The output should follow this format:
    .
    - file1.py
    - readme.md
    - dir1/
        - dir5/
          - dir6/
          - dir7/
    - dir2/
        - dir3
        - dir4
    """
    def list_dir_tree(path, indent):
        entries = []
        try:
            items = sorted(os.listdir(path))
        except FileNotFoundError:
            return []
        for item in items:
            if item.startswith('.'):
                continue  # skip hidden files/dirs
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                entries.append('  ' * indent + f'- {item}/')
                entries.extend(list_dir_tree(full_path, indent + 1))
            else:
                if indent == 0:
                    entries.append('  ' * indent + f'- {item}')
        return entries

    print("Getting project structure...")
    structure = ['.']
    structure.extend(list_dir_tree('.', 0))
    return '\n'.join(structure)

@function_tool
def write_report(files: list[str], implementation_summary: str) -> str:
    """Write a report of the changes to the codebase."""
    return "The report is as follows: " + implementation_summary

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
    if len(argv) < 2:
        request = input("Enter a request: ")
    else:
        request = argv[1]

    agent = Agent(
        name="Codebase Agent",
        model="o4-mini",
        tools=[list_files, cat_file, grep_file, get_project_structure],
        instructions="""
You're an expert software developer tasked with analyzing a codebase to identify the most relevant files for implementing a feature request or fixing a bug. Your goal is to thoroughly understand the codebase structure and dependencies before suggesting any implementation approach.

## Available Tools:
- get_project_structure: Get the project structure of the codebase.
- list_files: List all files in a directory.
- cat_file: Read a file and return the whole contents.
- grep_file: Search for a pattern in a file using Python's re.search and return the lines around the match.

## Required Workflow (Follow these steps in order):

1. **Initial Assessment**:
   - ALWAYS begin by using get_project_structure to understand the overall codebase organization.
   - Identify the type of codebase or framework based on key directories, file patterns, and configuration files.
   - Assess the approximate size and complexity of the codebase.
   - Report what you've learned about the project type (e.g., "This appears to be a React application with a Node.js backend" or "This is a single-file Python script").

2. **Adaptive Exploration Strategy**:
   - For small codebases (1-5 files): Examine each file thoroughly to understand its purpose.
   - For medium codebases: Identify core files by examining configuration files, entry points, and directories that match the feature domain.
   - For large codebases: Use grep_file strategically to search for terms related to the feature request across the codebase.
   - Always adapt your approach based on what you discover about the codebase structure.

3. **Code Understanding**:
   - Use cat_file to read important files fully. YOU MUST READ AT LEAST ONE IMPLEMENTATION FILE COMPLETELY.
   - Use grep_file to search for relevant terms related to the feature/bug.
   - Document specific patterns you observe in the existing code related to your task.
   - Map relationships between key components and how data flows through the system.
   - Build a mental model of the application architecture proportional to its complexity.
   - Note the coding style, error handling approaches, and documentation conventions.

4. **Comprehensive Analysis**:
   - Identify the relevant files that would likely need modification.
   - The number of files to examine should be proportional to the codebase size and complexity.
   - For each key file, explain its purpose in the system and why it's relevant.
   - Note any dependencies or side effects that changes might have.

5. **Implementation Planning**:
   - Only after thorough exploration, provide a detailed plan for implementation.
   - Specify which files need to be modified and what changes are needed.
   - If suggesting new files, clearly justify why existing files cannot be modified instead.
   - Explain how your proposed changes integrate with the existing architecture.

## Critical Guidelines:
- NEVER suggest creating new files without first understanding the existing code structure.
- NEVER give up exploration after just checking the project structure without deeper investigation.
- Adjust exploration depth based on codebase size: more files for larger projects, complete analysis for smaller ones.
- If you're uncertain about which files are relevant, use grep_file to search for keywords related to the feature.
- Consider common patterns in the codebase to ensure your suggestions maintain consistency.
- **Do not try to list files or directories that don't exist.**
- ALWAYS examine the implementation of at least one similar feature before proposing changes.
- For any new functionality, you MUST first check existing implementations of similar features to understand coding patterns and standards.
- When suggesting tool implementations, your code should mirror the style, parameter handling, docstring format, and error handling of existing similar tools.
- You MUST use cat_file or grep_fileon key implementation files before making specific code recommendations.
- Do not finish your response until you have followed all of the steps above.

## Final Response Format:
1. **Codebase Structure Summary**: Brief overview of the project type, architecture, and size.
2. **Key Files Examined**: List of files you checked and why they're relevant.
3. **Understanding of Current Implementation**: How the related functionality currently works.
4. **Implementation Recommendations**: Specific files to modify and what changes to make.
5. **Reasoning**: Explain why your suggested approach is appropriate for this codebase.
        """
    )

    print("Starting...")
    result = Runner.run_sync(agent, max_turns=50, input=request)
    print(result.final_output)
