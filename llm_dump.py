from pydantic import BaseModel, DirectoryPath, FilePath
from pathlib import Path
from typing import List, Set, Optional
import os
import re
from pathspec import PathSpec

class FileContent(BaseModel):
    file_path: FilePath
    content: str

class FolderTraversalInput(BaseModel):
    folder_path: DirectoryPath
    output_file: str

class ObsidianTraversalInput(BaseModel):
    start_file: str
    output_file: str
    max_depth: int = 2
    base_folder: Optional[DirectoryPath] = None

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

def extract_markdown_links(content: str) -> Set[str]:
    """
    Extract both Obsidian wiki-style links and standard markdown links from content.
    """
    # Match Obsidian wiki-style links [[link]] or [[link|alias]], excluding the alias part
    wiki_links = set()
    for match in re.findall(r'\[\[(.*?)\]\]', content):
        # Split on pipe and take the first part (the actual link)
        wiki_links.add(match.split('|')[0])
        
    # Match standard markdown links [text](link), excluding external links
    md_links = set()
    for link in re.findall(r'\[(?:[^\]]*)\]\(([^)]+)\)', content):
        if not link.startswith(('http://', 'https://', 'ftp://')):
            md_links.add(link)
    
    # Remove any anchor tags (#) from all links
    cleaned_links = {link.split('#')[0] for link in wiki_links.union(md_links)}
    return cleaned_links

def process_markdown_file(file_path: Path, base_folder: Path) -> FileContent:
    """
    Read a markdown file and return its content.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return FileContent(file_path=file_path, content=content)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def ensure_md_extension(file_path: str) -> str:
    """
    Ensure the file path ends with .md extension
    """
    if not file_path.endswith('.md'):
        return f"{file_path}.md"
    return file_path

def traverse_markdown_files(input_data: ObsidianTraversalInput, visited: Set[Path] = None, current_depth: int = 0):
    """
    Traverse markdown files starting from the input file up to max_depth, collecting all content.
    """
    if visited is None:
        visited = set()
    
    base_folder = input_data.base_folder or Path.cwd()
    current_file = base_folder / ensure_md_extension(input_data.start_file)
    
    if not current_file.is_file():
        raise ValueError(f"File not found: {current_file}")
    
    if current_file in visited:
        return []
    
    visited.add(current_file)
    file_content = process_markdown_file(current_file, base_folder)
    if not file_content:
        return []
    
    results = [file_content]
    
    # Only process links if we haven't reached max_depth
    if current_depth >= input_data.max_depth:
        return results
    
    # Extract and process links
    links = extract_markdown_links(file_content.content)
    for link in links:
        resolved_path = resolve_markdown_link(link, current_file, base_folder)
        if resolved_path and resolved_path not in visited:
            # For nested files, use path relative to base_folder
            nested_start = str(resolved_path.relative_to(base_folder))
            nested_input = ObsidianTraversalInput(
                start_file=nested_start,
                output_file=input_data.output_file,
                max_depth=input_data.max_depth,
                base_folder=base_folder
            )
            nested_results = traverse_markdown_files(nested_input, visited, current_depth + 1)
            results.extend(nested_results)
    
    return results

def resolve_markdown_link(link: str, current_file: Path, base_folder: Path) -> Optional[Path]:
    """
    Resolve a markdown link to an actual file path.
    """
    # Handle relative paths (../file)
    if link.startswith('../'):
        potential_path = current_file.parent.parent / link[3:]
    else:
        # If the link doesn't start with '../', try resolving from current file's directory first
        potential_path = current_file.parent / link
        if not potential_path.exists():
            # If not found, try from base folder
            potential_path = base_folder / link

    # Ensure .md extension
    potential_path = potential_path.parent / ensure_md_extension(potential_path.name)
    
    # Check if the file exists
    if potential_path.exists():
        return potential_path
    return None

def dump_markdown_files(input_data: ObsidianTraversalInput):
    """
    Process markdown files and their links, combining them into a single output file.
    """
    # If base_folder is not provided, use the parent directory of the start file
    if not input_data.base_folder:
        input_data.base_folder = Path(input_data.start_file).parent

    files = traverse_markdown_files(input_data)
    
    with open(input_data.output_file, 'w', encoding='utf-8') as output_file:
        for file_content in files:
            relative_path = file_content.file_path.relative_to(input_data.base_folder)
            output_file.write(f"--- Start of {relative_path} ---\n")
            output_file.write(file_content.content + "\n")
            output_file.write(f"--- End of {relative_path} ---\n\n")

def main():
    """
    Entry point for CLI execution.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Process various content sources for LLM context.")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Git repository dump command
    git_parser = subparsers.add_parser("git", help="Dump the contents of a git repository")
    git_parser.add_argument("folder_path", type=str, help="Path to the repository to process")
    git_parser.add_argument("output_file", type=str, help="Path to the output text file")

    # Markdown command
    md_parser = subparsers.add_parser("markdown", help="Process Obsidian/markdown files")
    md_parser.add_argument("start_file", type=str, help="Path to the starting markdown file")
    md_parser.add_argument("output_file", type=str, help="Path to the output text file")
    md_parser.add_argument("--max-depth", type=int, default=2, help="Maximum depth to traverse (default: 2)")
    md_parser.add_argument("--base-folder", type=str, help="Base folder for resolving links (default: start file's folder)")

    args = parser.parse_args()

    if args.command == "git":
        folder_input = FolderTraversalInput(folder_path=args.folder_path, output_file=args.output_file)
        dump_files_to_text(folder_input)
    elif args.command == "markdown":
        md_input = ObsidianTraversalInput(
            start_file=args.start_file,
            output_file=args.output_file,
            max_depth=args.max_depth,
            base_folder=args.base_folder
        )
        dump_markdown_files(md_input)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 