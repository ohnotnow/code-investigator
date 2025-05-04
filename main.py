from pydantic import BaseModel
from agents import Agent, Runner, function_tool
import argparse
import re
import os
from helpers.project_type import ProjectTypeAgent

docs_prompt = """
You're an expert software architect and technical writer tasked with analyzing a codebase to create comprehensive documentation. Your goal is to thoroughly understand what the application actually does, its architecture, design patterns, control flow, and organization by examining the actual implementation code in depth.

## Available Tools:
- get_project_structure: Get the project structure of the codebase.
- list_files: List all files in a directory.
- cat_file: Read a file and return the whole contents.
- grep_file: Search for a pattern in a file using Python's re.search and return the lines around the match.

## Required Workflow (Follow these steps in order):

1. **Initial Project Structure Assessment**:
   - Begin by using get_project_structure to understand the overall codebase organization.
   - Identify the type of codebase or framework based on configuration files.
   - This is just the starting point - do NOT draw conclusions about the application's purpose yet.

2. **Core File Examination (MANDATORY)**:
   - CRITICAL: You MUST read at least 5-10 actual implementation files in full using cat_file.
   - Focus on:
     * Controllers/route handlers that indicate main user flows
     * Model definitions that reveal the domain objects
     * Service classes that implement core business logic
     * View/template files that show user interfaces
   - DO NOT rely solely on configuration files, package lists, or readme files.
   - The application's true purpose can only be determined by examining implementation code.

3. **Application Purpose Discovery**:
   - Based on ACTUAL CODE examination (not configuration), determine:
     * What problem does this application solve?
     * Who are the users and what actions can they perform?
     * What data entities are central to the application?
   - Use actual class and method names, variable names, and comments in the code to identify purpose.
   - Document specific evidence from the code that supports your conclusions.

4. **Control Flow Tracing**:
   - Locate and analyze entry points (main controllers, index files, etc.)
   - Trace at least TWO complete user journeys through the code from request to response.
   - Map how control passes between components for key operations.
   - Examine actual implementation of request handling, not just route definitions.

5. **Data Flow Analysis**:
   - Examine how data is:
     * Input (forms, APIs, imports)
     * Validated and sanitized
     * Processed and transformed
     * Persisted or transmitted
     * Retrieved and displayed
   - Analyze ACTUAL queries, data transformations, and model interactions.

6. **Design Pattern Identification**:
   - Identify patterns based on ACTUAL implementation code, not assumptions.
   - Provide specific code examples that demonstrate each pattern.
   - Note custom patterns unique to this codebase with concrete examples.

7. **Integration Points Catalog**:
   - Identify and examine all external system integrations.
   - Document APIs consumed and provided.
   - Analyze authentication mechanisms and data exchange formats.

8. **Documentation Synthesis**:
   - Synthesize findings with SPECIFIC CODE EXAMPLES for each major point.
   - Create clear documentation that accurately represents what the code ACTUALLY does.
   - Ensure documentation is based on code evidence, not framework assumptions.

## Critical Guidelines:
- NEVER draw conclusions about application functionality without reading actual implementation code.
- Always provide specific evidence from the code (file names, class names, method names, etc.) for your claims.
- Configuration files and dependencies provide clues, but implementation details are authoritative.
- Examine at least 2-3 files from EACH major component type (controllers, models, services, etc.).
- When documenting patterns, include specific code snippets or file references as evidence.
- Ensure you understand custom abstractions specific to this project beyond framework defaults.
- The bulk of your investigation time should be spent reading implementation files, not configuration.
- If it is a known project type, you MUST read the relevant config file (e.g. package.json, composer.json, etc.) to get a better understanding of the project, dependancies, langauge/framework versions.

## Final Documentation Format:
1. **Project Overview**: Actual purpose based on code evidence, not just framework identification. If you do not know the name of the project - make up a suitable name.
2. **Core Functionality**: Key features implemented with specific evidence from code.
3. **Data Model**: Principal entities and their relationships as implemented in code.
4. **Application Flow**: How requests are processed with specific paths through the code.
5. **Integration Points**: External systems interaction with implementation details.
6. **Design Patterns**: Patterns observed in the actual code with specific examples.
7. **Code Organization**: How the codebase is structured beyond framework conventions.
8. **Developer Guidelines**: Conventions inferred from actual implementation.

For each section, include:
- Specific file references
- Relevant class/method names
- Short code excerpts as evidence
- How these elements work together

## Local development notes
If the project is a Laravel project, you should know the following:
- We use the 'lando' tool to run development servers (always mention the URL https://lando.dev/).
- To run the project, copy .env.example to .env and run 'lando start'
- Lando will start the project and show you the URLs in the terminal
- You can run `lando mfs` to run the migrations and seeders
- You can run `lando test` to run the tests

If the project is a Python project, you should know the following:
- We use the 'uv' tool to run development servers (https://docs.astral.sh/uv/getting-started/installation/).
- To install dependencies, run `uv sync`
- To run the project, run `uv run main.py` (or whatever the main file is)

## Final note
The quality of your documentation depends on the depth of your code analysis. Focus on what the application actually does according to the implementation code, not what you think it might do based on the framework or library choices. Your documentation should reflect the reality of the codebase, not assumptions.
"""

code_prompt = """
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

## Final note
Your response will be read by another LLM in order for it to actually implement your instructions.  So please be clear in your guidence to keep the LLM focussed and on-mission.

"""
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
        try:
            items = sorted(os.listdir(path))
        except FileNotFoundError:
            return []
        for item in items:
            if item.startswith('.'):
                continue  # skip hidden files/dirs
            if item == 'node_modules' or item == 'vendor' or item == 'dist' or item == 'build' or item == 'public' or item == 'cache' or item == 'logs':
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                file_count = len(os.listdir(full_path))
                entries.append('  ' * indent + f'- {item}/ ({file_count} {file_count == 1 and 'file' or 'files'})')
                entries.extend(list_dir_tree(full_path, indent + 1))
            else:
                if indent == 0:
                    entries.append('  ' * indent + f'- {item}')
        return entries

    print("- Getting project structure...")
    structure = ['.']
    structure.extend(list_dir_tree('.', 0))
    project_type = ProjectTypeAgent('.').run()
    project_info = f"\n\n## Estimated project type : {project_type.language} / {project_type.framework}\n\n"
    output = '\n'.join(structure)
    output += project_info
    return output

@function_tool
def write_report(files: list[str], implementation_summary: str) -> str:
    """Write a report of the changes to the codebase."""
    return "The report is as follows: " + implementation_summary

@function_tool
def list_files(directory: str, recursive: bool) -> str:
    """List all files in a directory."""
    print(f"- Listing files in {directory} {'recursively' if recursive else ''}")
    file_list = ""
    if recursive:
        files = []
        # We only want to list regular files and directories - ignore dotfiles
        for root, dirs, current_files in os.walk(directory):
            # Filter out dot directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            # filter out known dependancy directories
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'vendor', 'dist', 'build', 'public']]
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
    print(f"- Reading {file_path}")
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"

@function_tool
def grep_file(file_path: str, python_regex_pattern: str, include_before_lines: int, include_after_lines: int) -> str:
    """Search for a python re.search pattern in a file and return the lines around the match."""
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

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--request", type=str, required=False)
    args.add_argument("--mode", type=str, required=False, default="code")
    args.add_argument("--model", type=str, required=False, default="o4-mini")
    args = args.parse_args()
    request = args.request
    mode = args.mode

    if mode == "code":
        prompt = code_prompt
    elif mode == "docs":
        prompt = docs_prompt
    else:
        raise ValueError(f"Invalid mode: {mode}")

    if not request and mode == "code":
        request = input("Enter a request: ")
    if not request and mode == "docs":
        request = "Please provide a GitHub style Readme.md for the codebase."

    agent = Agent(
        name=f"{mode.capitalize()} Agent",
        model=args.model,
        tools=[list_files, cat_file, grep_file, get_project_structure],
        instructions=prompt
    )

    print(f"\n\n- Starting agent using {args.model}...")
    result = Runner.run_sync(agent, max_turns=50, input=request)
    print(f"\n\n- Final output:\n\n")
    print(result.final_output)
