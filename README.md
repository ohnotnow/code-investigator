# code-investigator

An AI-powered tool for exploring and summarizing code repositories.  
It provides a “Codebase Agent” with three built-in tools:
- **list_files**: list files in a directory (optionally recursive)  
- **cat_file**: read and return a file’s contents  
- **grep_file**: search for a regex pattern in a file and return matching lines with context  

The agent can be extended with new tools (e.g. an `rm_file` tool) and driven by feature requests to pinpoint relevant files for implementation guidance.

---

## Table of Contents
1. [Installation](#installation)  
2. [Usage](#usage)  
3. [Examples](#examples)  
4. [Configuration](#configuration)  
5. [Extending the Agent](#extending-the-agent)  
6. [License](#license)  

---

## Installation

Prerequisites  
- Git  
- Python 3.8+ (installed)  
- `uv` tool (see https://docs.astral.sh/uv/)  

Clone the repository and install dependencies:

```bash
# Clone
git clone https://github.com/ohnotnow/code-investigator.git
cd code-investigator

# Install dependencies (all platforms)
uv sync
```

No platform-specific steps are required—`uv sync` reads your project’s declared dependencies and installs them in a virtual environment automatically.

---

## Usage

Run the main script with `uv`:

```bash
uv run main.py
```

By default, this will:

1. Instantiate the Codebase Agent with GPT-4.1 and the three tools.  
2. Execute the sample prompt:  
   > “Could we add an rm_file tool to the codebase and make it available to the agent?”  

To adjust the prompt or parameters, modify the call at the bottom of `main.py`:

```python
result = Runner.run_sync(
    agent,
    input="Your custom feature request here"
)
```

Then rerun:

```bash
uv run main.py
```

---

## Examples

Listing files recursively in the current directory from within the agent’s code:
```python
list_files(directory=".", recursive=True)
```

Reading a specific file:
```python
cat_file(file_path="agents.py")
```

Searching for a function definition in a file with context:
```python
grep_file(
  file_path="main.py",
  python_regex_pattern=r"def list_files",
  include_before_lines=2,
  include_after_lines=2
)
```

---

## Configuration

No environment variables are required by default. If you integrate with an external model provider that needs an API key (e.g. OpenAI), set the appropriate variable in your shell:

```bash
export OPENAI_API_KEY="your_api_key"
```

---

## Extending the Agent

To add a new tool (for example, `rm_file`):

1. Define a new function and decorate it with `@function_tool`.
2. Implement the logic inside.
3. Pass the function into the agent’s `tools` list in `main.py`.

Example skeleton:

```python
@function_tool
def rm_file(file_path: str) -> str:
    """Remove a file and return status."""
    # remove file logic here
    return f"Removed {file_path}"
```

Then update:

```python
agent = Agent(
    name="Codebase Agent",
    model="gpt-4.1",
    tools=[list_files, cat_file, grep_file, rm_file],
    instructions="…"
)
```

---

## License

This project is licensed under the MIT License.
