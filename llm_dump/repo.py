from pathlib import Path
import click
from pathspec import PathSpec
from typing import List
import os
from llm_dump.utility_types import FileContent, FolderTraversalInput
from llm_dump.group import cli  # Import from group instead of cli

def load_gitignore(folder: Path) -> PathSpec:
    """
    Load .gitignore file and parse it into a PathSpec object.
    Always includes .git directory in ignored patterns.
    """
    # Default patterns that should always be ignored
    default_patterns = [
        ".git/",
        ".git/**/*"
    ]
    
    gitignore_path = folder / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            patterns = list(f) + default_patterns
            return PathSpec.from_lines("gitwildmatch", patterns)
    
    return PathSpec.from_lines("gitwildmatch", default_patterns)

def generate_file_tree(folder: Path, prefix="", pathspec=None, base_folder=None) -> str:
    """
    Recursively generate a tree structure for a given folder, respecting .gitignore.
    """
    if base_folder is None:
        base_folder = folder
    
    tree = []
    entries = sorted(folder.iterdir(), key=lambda x: (x.is_file(), x.name))
    
    for idx, entry in enumerate(entries):
        # Compute the relative path from the base_folder
        relative_entry = entry.relative_to(base_folder).as_posix()
        if entry.is_dir():
            relative_entry += '/'
            
        if pathspec and pathspec.match_file(relative_entry):
            continue  # Skip ignored files
            
        is_last = idx == len(entries) - 1
        connector = "└── " if is_last else "├── "
        
        # Add the current entry
        tree.append(f"{prefix}{connector}{entry.name}")
        
        # Recursively process directories
        if entry.is_dir():
            next_prefix = prefix + ("    " if is_last else "│   ")
            subtree = generate_file_tree(entry, next_prefix, pathspec, base_folder)
            if subtree:  # Only add non-empty subtrees
                tree.append(subtree)
    
    return "\n".join(tree)

def traverse_folder(folder_path: Path, pathspec=None) -> List[FileContent]:
    """
    Recursively traverse a folder and collect file contents, respecting .gitignore.
    """
    file_contents = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = Path(root) / file
            relative_path = file_path.relative_to(folder_path).as_posix()
            if pathspec and pathspec.match_file(relative_path):
                continue  # Skip ignored files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                file_contents.append(FileContent(file_path=file_path, content=content))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    return file_contents

def dump_files_to_text(input_data: FolderTraversalInput):
    """
    Dump the folder's file contents and tree structure into a single text file, respecting .gitignore.
    """
    folder_path = Path(input_data.folder_path)
    output_path = Path(input_data.output_file)

    # Load .gitignore rules if present
    pathspec = load_gitignore(folder_path)
    
    # Generate the file tree
    tree_structure = generate_file_tree(folder_path, pathspec=pathspec)
    
    # Traverse the folder and collect file contents
    files = traverse_folder(folder_path, pathspec=pathspec)
    
    # Write to the output file
    with open(output_path, 'w', encoding='utf-8') as output_file:
        # Write the tree structure
        output_file.write("File Tree Structure:\n")
        output_file.write(tree_structure + "\n\n")
        
        # Write the content of each file
        for file_content in files:
            output_file.write(f"--- Start of {file_content.file_path.relative_to(folder_path)} ---\n")
            output_file.write(file_content.content + "\n")
            output_file.write(f"--- End of {file_content.file_path.relative_to(folder_path)} ---\n\n")

@cli.command()  # Use cli.command() instead of click.command()
@click.argument('folder_path', type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.argument('output_file', type=click.Path(dir_okay=False))
def git(folder_path: Path, output_file: str):
    """Dump the contents of a git repository.
    
    FOLDER_PATH is the path to the repository to process
    OUTPUT_FILE is the path to the output text file
    """
    folder_input = FolderTraversalInput(folder_path=folder_path, output_file=output_file)
    dump_files_to_text(folder_input)
