from pydantic import BaseModel
from agents import Agent, Runner, function_tool, ModelSettings
import argparse
import re
from pathlib import Path
from helpers.project_type import ProjectTypeAgent
import time
import subprocess

docs_prompt = """
You're an expert software architect and technical writer tasked with analyzing a codebase to create comprehensive documentation. Your goal is to thoroughly understand what the application actually does, its architecture, design patterns, control flow, and organization by examining the actual implementation code in depth.

## Available Tools:
- get_project_structure: Get the project structure of the codebase.
- list_files: List all files in a directory.
- cat_file: Read a file and return the whole contents.
- grep_file: Search for a pattern in a file using Python's re.search and return the lines around the match.
- get_git_remotes: Get the git remotes for the codebase (use this to help you write the installation instructions for `git clone`ing the codebase).

## Required Workflow (Follow these steps in order):

1. **Initial Project Structure Assessment**:
   - Begin by using get_project_structure to understand the overall codebase organization.
   - Identify the type of codebase or framework based on configuration files.
   - Use the get_git_remotes tool to get the git remotes for the codebase so you can write accurate `git clone` instructions.
   - This is just the starting point - do NOT draw conclusions about the application's purpose yet.

2. **Core File Examination (MANDATORY)**:
   - CRITICAL: You MUST read at actual implementation files in full using cat_file.
   - Depending on the size of the project, you may read more files to get a better understanding of the codebase.
     - A small project as around 100 files.  You MUST read at least 5-10 files.
     - A medium project as around 300+ files.  You MUST read at least 10-20 files.
     - A large project as around 1000+ files.  You MUST read at least 30-40 files.
   - DO NOT just read the Readme file - you MUST explore and read the codebase.
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
- Examine at least 2-3 files from EACH major domain in the project (for small projects this is controllers, models, services, etc., for large projects this is logical domains, like users, products, orders, etc.).
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
**ALWAYS** use the get_git_remotes tool to get the git remotes for the codebase - otherwise the user reading your report will not know how to clone the codebase.

If the project is a Laravel project, you should know the following:
- We use the 'lando' tool to run development servers (always mention the URL https://lando.dev/).
- To run the project, copy .env.example to .env and run 'lando start' then 'lando composer install'
- The .env.example file will have all entries set to work with the lando server already.
- Lando will start the project and show you the URLs in the terminal
- You can run `lando mfs` to run the migrations and seeders
- You can run `lando test` to run the tests
- We do not use docker or docker compose - we use lando - even if there is a docker-compose.yml file.

If the project is a Python project, you should know the following:
- We use the 'uv' tool to run development servers (https://docs.astral.sh/uv/getting-started/installation/).
- To install dependencies, run `uv sync`
- To run the project, run `uv run main.py` (or whatever the main file is)

## Final note
The quality of your documentation depends on the depth of your code analysis. Focus on what the application actually
does according to the implementation code, not what you think it might do based on the framework, project structure
or library choices. Your documentation should reflect the reality of the codebase, not assumptions.  IT IS CRITICAL
THAT YOU DO NOT MAKE ASSUMPTIONS ABOUT THE CODEBASE.  YOU MUST READ THE CODEBASE TO UNDERSTAND IT.  Imagine you were presented
with your own report and had to understand the codebase from scratch.  You must be able to explain the codebase to someone else
who has no idea what it is.
"""

code_prompt = """
You're an expert software developer tasked with analyzing a codebase to identify the most relevant files for implementing a feature request or fixing a bug. Your goal is to thoroughly understand the codebase structure and dependencies before suggesting any implementation approach.

## Available Tools:
- get_project_structure: Get the project structure of the codebase.
- list_files: List all files in a directory.
- cat_file: Read a file and return the whole contents.
- grep_file: Search for a pattern in a file using Python's re.search and return the lines around the match.
- get_git_remotes: Get the git remotes for the codebase.

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

mermaid_prompt = """
# Laravel Flow Diagram Agent

You're an expert Laravel developer tasked with analyzing a codebase to create detailed Mermaid diagrams that visualize the flow of operations for specific user journeys or system processes. Your goal is to trace how data and control flows through the application, from routes to controllers to models to views, and create a comprehensive flowchart.

## Available Tools:
- get_project_structure: Get the project structure of the codebase.
- list_files: List all files in a directory.
- cat_file: Read a file and return the whole contents.
- grep_file: Search for a pattern in a file using Python's re.search and return the lines around the match.
- get_git_remotes: Get the git remotes for the codebase.

## Required Workflow (Follow these steps in order):

1. **Initial Assessment**:
   - ALWAYS begin by using get_project_structure to understand the overall codebase organization.
   - Confirm this is a Laravel application by checking for key directories (app, routes, resources, config).
   - Identify if the project uses additional frameworks (Livewire, Inertia, etc.).
   - Report what you've learned about the project structure (e.g., "This is a Laravel application with Livewire components").

2. **Route Discovery**:
   - Examine routes files in the routes directory (web.php, api.php, etc.) to find entry points related to the requested user journey.
   - Identify the controllers and methods that handle these routes.
   - For Laravel 8+, look for controller route definitions using the Route::controller syntax.
   - For Livewire components, check routes for Livewire::component registrations.
   - Document all relevant routes that relate to the requested flow diagram.
   - Modern Laravel projects use the [ControllerName::class, 'method'] syntax for controllers.

3. **Controller Analysis**:
   - Locate and analyze the relevant controllers in app/Http/Controllers.
   - For each controller method, identify:
     - Input validation (FormRequests or inline validation)
     - Model interactions
     - Service class calls
     - Response/view returns
   - For Livewire components, check app/Http/Livewire directory for component classes.
   - Track the flow of data through each controller method.

4. **Model Interaction Mapping**:
   - Identify models used in the controllers (typically in app/Models).
   - Examine key model methods, relationships, and events relevant to the flow.
   - Look for special Laravel features like observers, events, and listeners that might be triggered.
   - Note any queued jobs or events dispatched during the process.

5. **View/Frontend Resolution**:
   - Locate view files referenced in the controllers (typically in resources/views).
   - For Livewire, check component view files.
   - For API endpoints, identify the response structure.
   - Note any JavaScript interactions that are crucial to the flow.

6. **Middleware Identification**:
   - Check for middleware applied to the relevant routes.
   - Analyze how middleware might affect the flow (authentication, validation, etc.).

7. **Generate Comprehensive Flow Diagram**:
   - Create a detailed Mermaid flowchart diagram that shows:
     - Entry points (routes)
     - Controller/method executions
     - Decision points and conditionals
     - Model interactions and database operations
     - View rendering or API responses
     - Error paths and exception handling
   - Use appropriate Mermaid syntax for different flow elements:
     - Start/end points
     - Process steps
     - Decision diamonds
     - Parallel processes if applicable
     - Subgraphs to group related processes

## Laravel-Specific Guidelines:
- For route discovery, check both closure-based and controller-based routes.
- Look for middleware groups that might affect multiple routes.
- Check for model events, observers, and service providers that might be part of the flow.
- For authentication flows, check auth configuration and the relevant providers.
- For form processing, trace the validation, storage, and response cycle.
- Look for queued jobs in app/Jobs that might be part of the flow.
- Check for Laravel events/listeners in app/Events and app/Listeners.

## Mermaid Diagram Guidelines:
- Use flowchart TD (top-down) or LR (left-right) direction based on complexity.
- Use SIMPLE alphanumeric node IDs without special characters (e.g., A1, UserAuth, DB1).
- IMPORTANT: Node IDs must be simple and cannot contain special characters, spaces, or punctuation.
- For node labels, use only basic characters inside square brackets: [Label text].
- Avoid using parentheses, colons, or special characters in node labels.
- For method names in labels, use dot notation without parentheses: "Controller.method" NOT "Controller@method" or "Controller->method()".
- Decision diamonds should use simple yes/no or true/false paths.
- Format subgraphs with proper syntax:
  ```
  subgraph Title
    Node1 --> Node2
  end
  ```
- Keep the diagram readable by using clear, concise labels.
- Include database operations explicitly.
- For very complex flows, break into multiple linked diagrams.
- ALWAYS validate your final Mermaid syntax for errors before submitting.

## Correct Shape Syntax:
- Process nodes: `A[Description]`
- Decision nodes: `B{Question?}`
- Database operations: `C[(Database)]`
- Input/output: `D>Result]`
- Start/end: `E([Start/End])`

## Example Mermaid Syntax:
```mermaid
flowchart TD
    Start([Begin Login Flow]) --> RouteLogin[Route login page]
    RouteLogin --> AuthCheck{Is authenticated?}
    AuthCheck -->|Yes| RedirectDash[Redirect to Dashboard]
    AuthCheck -->|No| LoginForm[Show Login Form]
    LoginForm --> SubmitForm[Submit Credentials]
    SubmitForm --> ValidateUser{Valid credentials?}
    ValidateUser -->|Yes| CreateSession[Create User Session]
    CreateSession --> RedirectToDash[Redirect to Dashboard]
    ValidateUser -->|No| ShowError[Display Error Message]
    ShowError --> LoginForm
    RedirectToDash --> End([End Login Flow])
    RedirectDash --> End
```

## Common Syntax Errors to Avoid:
1. Using special characters in node IDs
2. Using parentheses or colons in node labels
3. Incorrect subgraph formatting
4. Missing end statements for subgraphs
5. Missing node definitions
6. Inconsistent arrow directions
7. Using PHP-specific syntax like @ or -> in node labels

## Syntax Validation Steps:
1. Verify all node IDs are simple alphanumeric strings
2. Check that all nodes referenced in connections are defined
3. Ensure all subgraphs have matching "end" statements
4. Confirm no special characters in node labels
5. Verify consistent arrow direction syntax (-->, not ->, etc.)
6. Ensure proper nesting of elements

## Final Response Format:
1. **Project Structure Summary**: Brief overview of the Laravel application structure.
2. **User Journey Overview**: Description of the flow being diagrammed.
3. **Key Components Identified**: List of routes, controllers, models, and views involved.
4. **Flow Explanation**: Textual description of the process flow.
5. **Mermaid Diagram**: Complete Mermaid flowchart code with verified syntax.
6. **Simplified Test Diagram**: A simpler version of the diagram with minimal nodes to verify basic syntax works.
7. **Diagram Explanation**: Breakdown of the major sections of the diagram.

## Syntax Verification Process:
Before submitting your final Mermaid diagram, you MUST:
1. Create a simplified test version with just 5-6 nodes to verify the basic structure works
2. Check that all node IDs are simple alphanumeric strings (A1, UserLogin, etc.)
3. Verify that node labels contain no special characters, parentheses, or @ symbols
4. Ensure all subgraphs have proper 'end' statements
5. Confirm all arrow syntax is consistent (-->)
6. Make sure no PHP-specific syntax appears in the diagram (like ->method() or @method)
7. Verify that the test diagram renders correctly in concept before expanding to the full diagram

Remember to focus on one specific user journey or system process at a time to keep the diagram manageable and useful. For complex applications, it may be necessary to create multiple diagrams for different aspects of the system.
"""

class FileSummary(BaseModel):
    files: list[str]
    implementation_summary: str

def filename_unsafe(filename: str) -> bool:
    # Disallow absolute paths
    p = Path(filename)
    if p.is_absolute():
        return True
    # Disallow parent directory traversal
    if any(part == '..' for part in p.parts):
        return True
    # Disallow paths that escape the current working directory
    try:
        resolved = (Path.cwd() / p).resolve()
        if not str(resolved).startswith(str(Path.cwd().resolve())):
            return True
    except Exception:
        return True
    return False

def count_files(structure_output: str) -> int:
    total_files = 0
    lines = structure_output.strip().split('\n')

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Check if line contains a file count
        if '(' in line and ' file' in line:
            # Extract the number between '(' and ' files)'
            file_count_str = line.split('(')[1].split(' file')[0]
            try:
                file_count = int(file_count_str)
                total_files += file_count
            except ValueError:
                # Skip if we can't parse the number
                pass
        # Check if it's a regular file (no directory indicator)
        elif not line.strip().endswith('/') and not ('(' in line and ' file' in line):
            # Count lines that represent individual files (they don't end with '/')
            # and don't contain a file count
            # Remove leading spaces and dash to check if it's a file entry
            clean_line = line.strip()
            if clean_line.startswith('- '):
                total_files += 1

    return total_files

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
    # project_info += f"\n\n## Total files: {total_files}\n\n"
    output = '\n'.join(structure)
    output += project_info
    total_files = count_files(output)
    output += f"\n\n## Total files: {total_files}\n\n"
    return output

@function_tool
def write_report(files: list[str], implementation_summary: str) -> str:
    """Write a report of the changes to the codebase."""
    return "The report is as follows: " + implementation_summary

@function_tool
def list_files(directory: str, recursive: bool) -> str:
    """List all files in a directory."""
    print(f"- Listing files in {directory} {'recursively' if recursive else ''}")
    if filename_unsafe(directory):
        return "Forbidden"
    file_list = ""
    if recursive:
        files = []
        for p in Path(directory).rglob("*"):
            if p.is_file() and not any(part.startswith('.') for part in p.parts) and not any(part in ['node_modules', 'vendor', 'dist', 'build', 'public'] for part in p.parts):
                files.append(str(p))
        files = sorted(set(files))
        file_list = "\n".join(files)
    else:
        try:
            files = []
            for file in Path(directory).iterdir():
                if not file.name.startswith("."):
                    files.append(str(file))
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
def get_git_remotes() -> str:
    """Get the git remotes for the codebase."""
    print(f"- Getting git remotes")
    result = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True, cwd='.')
    return result.stdout

def is_a_valid_file(file_path: str) -> bool:
    return Path(file_path).exists() and Path(file_path).is_file()

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

def estimate_cost(total_input_tokens: int, total_output_tokens: int, model: str) -> float|str:
    if model == "o4-mini":
        input_cost = (total_input_tokens / 1_000_000) * 2.00
        output_cost = (total_output_tokens / 1_000_000) * 8.00
        return input_cost + output_cost
    elif model == "gpt-4.1":
        input_cost = (total_input_tokens / 1_000_000) * 1.10
        output_cost = (total_output_tokens / 1_000_000) * 4.40
        return input_cost + output_cost
    elif model == "o3":
        input_cost = (total_input_tokens / 1_000_000) * 10.00
        output_cost = (total_output_tokens / 1_000_000) * 40.00
        return input_cost + output_cost
    else:
        return "Unknown model"

def print_usage(result, model, total_time_in_seconds):
    print(f"\n\n- Usage:")
    total_input_tokens = 0
    total_output_tokens = 0
    for response in result.raw_responses:
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens
    print(f"  - Total input tokens: {total_input_tokens}")
    print(f"  - Total output tokens: {total_output_tokens}")
    cost = estimate_cost(total_input_tokens, total_output_tokens, model)
    print(f"  - Total cost: ${cost}")
    print(f"  - Total time taken: {total_time_in_seconds} seconds")

if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("--request", type=str, required=False)
    args.add_argument("--mode", type=str, required=False, default="code")
    args.add_argument("--model", type=str, required=False, default="o4-mini")
    args.add_argument("--no-readme", action="store_true", required=False, default=False)
    args = args.parse_args()
    request = args.request
    mode = args.mode

    if mode == "code":
        prompt = code_prompt
    elif mode == "docs":
        prompt = docs_prompt
    elif mode == "mermaid":
        prompt = mermaid_prompt
    else:
        raise ValueError(f"Invalid mode: {mode}")

    request = ""
    if mode == "code" or mode == "mermaid":
        if not args.request:
            request = input("Enter a request: ")
        else:
            request = args.request
    elif mode == "docs":
        if not args.no_readme:
            request = f"Please provide a GitHub style Readme.md for the codebase."
        if args.request:
            request += f"\n\n## User note\n\n{args.request}"
    else:
        print(f"Invalid mode: {mode}")
        exit(1)

    if not request:
        print("No request provided or inferrable from mode")
        exit(1)

    start_time = time.time()
    agent = Agent(
        name=f"{mode.capitalize()} Agent",
        model=args.model,
        tools=[list_files, cat_file, grep_file, get_project_structure, get_git_remotes],
        instructions=prompt,
        model_settings=ModelSettings(include_usage=True)
    )

    print(f"\n\n- Starting agent using {args.model}...")
    result = Runner.run_sync(agent, max_turns=50, input=request)
    print(f"\n\n- Agent finished")
    end_time = time.time()
    total_time_in_seconds = round(end_time - start_time, 2)
    print_usage(result, args.model, total_time_in_seconds)
    print(f"\n\n- Final output:\n\n")
    print(result.final_output)
