"""
This module contains utilities for file operations.
"""

import re
from pathlib import Path


def filename_unsafe(filename: str) -> bool:
    """
    Check if a filename is unsafe to access.

    Args:
        filename: The filename to check

    Returns:
        True if the filename is unsafe, False otherwise
    """
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


def is_a_valid_file(file_path: str) -> bool:
    """
    Check if a file path points to an existing file.

    Args:
        file_path: The file path to check

    Returns:
        True if the file exists, False otherwise
    """
    return Path(file_path).exists() and Path(file_path).is_file()


def is_a_valid_directory(directory: str) -> bool:
    """
    Check if a directory path points to an existing directory.

    Args:
        directory: The directory path to check

    Returns:
        True if the directory exists, False otherwise
    """
    return Path(directory).exists() and Path(directory).is_dir()


def count_files(structure_output: str) -> int:
    """
    Count the total number of files mentioned in a project structure output.

    Args:
        structure_output: The output string from get_project_structure

    Returns:
        The total number of files
    """
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


def strip_markdown(text: str) -> str:
    """
    Strip markdown code blocks from the start and end of text.

    Args:
        text: The text to process

    Returns:
        The text with markdown code blocks removed
    """
    lines = text.split('\n')
    if lines[0].startswith('```markdown') or lines[0].startswith('```'):
        lines = lines[1:]
    if lines[-1].endswith('```'):
        lines = lines[:-1]
    return '\n'.join(lines)


def sanitise_mermaid_syntax(text: str) -> str:
    """
    Find all mermaid code blocks and ensure node IDs are alphanumeric (no special characters or spaces),
    and node labels do not contain forbidden characters (parentheses, colons, @, <, >, &, etc).
    Only sanitize labels in valid node and edge definitions while preserving overall structure.

    Args:
        text: The text containing mermaid diagrams to process

    Returns:
        The text with sanitized mermaid syntax
    """
    def sanitise_node_id(node_id):
        # Only allow alphanumeric and underscores
        return re.sub(r'[^A-Za-z0-9_]', '_', node_id)

    def sanitise_label(label):
        # Remove forbidden characters from labels
        return re.sub(r'[()@:<>&]', '', label)

    def process_mermaid_block(block):
        lines = block.split('\n')
        new_lines = []

        for line in lines:
            # Skip comment lines or directive lines
            if re.match(r'\s*%%', line) or re.match(r'\s*flowchart', line) or re.match(r'\s*subgraph', line) or line.strip() == 'end':
                new_lines.append(line)
                continue

            # First pass: sanitize node IDs in isolation (before looking at connections)
            # This is for node definitions like: NodeID[Label]
            node_pattern = re.compile(r'([A-Za-z0-9_\-]+)([\[\{\(][^\]\}\)]*[\]\}\)])')
            for match in node_pattern.finditer(line):
                node_id, label_part = match.groups()
                clean_id = sanitise_node_id(node_id)
                # Extract and clean the label text
                label_match = re.match(r'([\[\{\(])([^\]\}\)]*)([\]\}\)])', label_part)
                if label_match:
                    open_br, label, close_br = label_match.groups()
                    clean_label = sanitise_label(label)
                    clean_label_part = f"{open_br}{clean_label}{close_br}"
                    # Replace just this node and label in the line
                    old_part = node_id + label_part
                    new_part = clean_id + clean_label_part
                    line = line.replace(old_part, new_part, 1)

            # Second pass: sanitize connections
            # This handles arrow patterns like: NodeA --> NodeB
            # We'll use word boundaries to avoid partial matches
            arrow_pattern = re.compile(r'\b([A-Za-z0-9_\-]+)\b\s*--?>+')
            for match in arrow_pattern.finditer(line):
                node_id = match.group(1)
                clean_id = sanitise_node_id(node_id)
                if node_id != clean_id:
                    # Replace just this node ID in the line, with word boundaries to avoid partial matches
                    line = re.sub(r'\b' + re.escape(node_id) + r'\b', clean_id, line, count=1)

            new_lines.append(line)

        return '\n'.join(new_lines)

    # Regex to find all mermaid code blocks
    def mermaid_block_iter(text):
        pattern = re.compile(r'(```mermaid(?:js)?\n)(.*?)(```)', re.DOTALL)
        for m in pattern.finditer(text):
            yield m

    # Replace each block with sanitised version
    new_text = text
    for m in mermaid_block_iter(text):
        block = m.group(2)
        processed = process_mermaid_block(block)
        new_text = new_text.replace(m.group(0), f'{m.group(1)}{processed}{m.group(3)}')

    return new_text
