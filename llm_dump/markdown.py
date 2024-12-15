from pathlib import Path
import re
from typing import Set, Optional
import click
from llm_dump.utility_types import ObsidianTraversalInput, FileContent
from llm_dump.group import cli

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

@cli.command()
@click.argument('start_file', type=click.Path(exists=True, dir_okay=False))
@click.argument('output_file', type=click.Path(dir_okay=False))
@click.option('--max-depth', type=int, default=2, help='Maximum depth to traverse (default: 2)')
@click.option('--base-folder', type=click.Path(exists=True, file_okay=False, dir_okay=True), help='Base folder for resolving links')
def markdown(start_file: str, output_file: str, max_depth: int, base_folder: Optional[str]):
    """Process Obsidian/markdown files.
    
    START_FILE is the path to the starting markdown file
    OUTPUT_FILE is the path to the output text file
    """
    md_input = ObsidianTraversalInput(
        start_file=start_file,
        output_file=output_file,
        max_depth=max_depth,
        base_folder=base_folder
    )
    dump_markdown_files(md_input)
