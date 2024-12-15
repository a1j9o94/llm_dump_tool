import pytest
from pathlib import Path
import tempfile
import os
import re

from llm_dump.utility_types import (
    FileContent,
    FolderTraversalInput,
    ObsidianTraversalInput,
)
from llm_dump.markdown import (
    extract_markdown_links,
    ensure_md_extension,
    traverse_markdown_files,
    dump_markdown_files,
)
from llm_dump.repo import (
    load_gitignore,
    generate_file_tree,
    traverse_folder,
    dump_files_to_text,
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)

@pytest.fixture
def sample_vault(temp_dir):
    """Create a sample Obsidian vault with interconnected files."""
    # Create main file
    main_file = temp_dir / "main.md"
    main_file.write_text("""# Main File
This is a test file with multiple links:
[[second_file]]
[[subfolder/third_file|Third]]
[External Link](https://example.com)
[[fourth_file#section]]
""")

    # Create second file
    second_file = temp_dir / "second_file.md"
    second_file.write_text("""# Second File
This links back to [[main]] and to [[subfolder/third_file]]
""")

    # Create subfolder and third file
    subfolder = temp_dir / "subfolder"
    subfolder.mkdir()
    third_file = subfolder / "third_file.md"
    third_file.write_text("""# Third File
This is in a subfolder and links to [[../main]]
""")

    # Create fourth file with anchor
    fourth_file = temp_dir / "fourth_file.md"
    fourth_file.write_text("""# Fourth File
This is the last file with no links
""")

    return temp_dir

def test_extract_markdown_links():
    """Test extraction of both wiki-style and standard markdown links."""
    content = """
    Here are some links:
    [[simple_link]]
    [[folder/nested_link]]
    [[aliased_link|Alias]]
    [Standard Link](standard.md)
    [[link_with_anchor#section]]
    """
    
    expected_links = {
        'simple_link',
        'folder/nested_link',
        'aliased_link',
        'standard.md',
        'link_with_anchor'
    }
    
    assert extract_markdown_links(content) == expected_links

def test_ensure_md_extension():
    """Test .md extension handling."""
    assert ensure_md_extension("file") == "file.md"
    assert ensure_md_extension("file.md") == "file.md"
    assert ensure_md_extension("folder/file") == "folder/file.md"
    assert ensure_md_extension("folder/file.md") == "folder/file.md"

def test_traverse_single_file(temp_dir):
    """Test traversal of a single file with no links."""
    file_path = temp_dir / "single.md"
    file_path.write_text("# Single File\nNo links here.")
    
    input_data = ObsidianTraversalInput(
        start_file="single.md",
        output_file="output.md",
        base_folder=temp_dir
    )
    
    results = traverse_markdown_files(input_data)
    assert len(results) == 1
    assert results[0].file_path == file_path
    assert "Single File" in results[0].content

def test_traverse_linked_files(sample_vault):
    """Test traversal of files with links."""
    input_data = ObsidianTraversalInput(
        start_file="main.md",
        output_file="output.md",
        base_folder=sample_vault,
        max_depth=2
    )
    
    results = traverse_markdown_files(input_data)
    
    # Should find all files except those beyond max_depth
    assert len(results) == 4
    
    # Verify all expected files are included
    file_names = {result.file_path.name for result in results}
    assert file_names == {"main.md", "second_file.md", "third_file.md", "fourth_file.md"}

def test_max_depth_limit(sample_vault):
    """Test that max_depth parameter correctly limits traversal."""
    input_data = ObsidianTraversalInput(
        start_file="main.md",
        output_file="output.md",
        base_folder=sample_vault,
        max_depth=1
    )
    
    results = traverse_markdown_files(input_data)
    
    # Should find main file and its directly linked files
    assert len(results) == 4
    
    # Files reached through secondary links should not be included
    file_names = {result.file_path.name for result in results}
    assert "main.md" in file_names

def test_cycle_handling(temp_dir):
    """Test handling of cyclic links between files."""
    # Create files with cyclic references
    (temp_dir / "a.md").write_text("[[b]]")
    (temp_dir / "b.md").write_text("[[c]]")
    (temp_dir / "c.md").write_text("[[a]]")
    
    input_data = ObsidianTraversalInput(
        start_file="a.md",
        output_file="output.md",
        base_folder=temp_dir
    )
    
    results = traverse_markdown_files(input_data)
    
    # Should visit each file exactly once
    assert len(results) == 3
    file_names = {result.file_path.name for result in results}
    assert file_names == {"a.md", "b.md", "c.md"}

def test_dump_markdown_files(sample_vault):
    """Test the complete file dumping process."""
    output_file = sample_vault / "output.md"
    
    input_data = ObsidianTraversalInput(
        start_file="main.md",
        output_file=str(output_file),
        base_folder=sample_vault
    )
    
    dump_markdown_files(input_data)
    
    # Verify output file exists and contains content
    assert output_file.exists()
    content = output_file.read_text()
    
    # Check that all file contents are included
    assert "Main File" in content
    assert "Second File" in content
    assert "Third File" in content
    assert "Fourth File" in content
    
    # Check file separators
    assert "--- Start of main.md ---" in content
    assert "--- End of main.md ---" in content 

def test_load_gitignore(temp_dir):
    """Test loading and parsing of .gitignore file."""
    # Create a .gitignore file
    gitignore_content = """
*.pyc
__pycache__/
.env
/dist/
node_modules/
"""
    (temp_dir / ".gitignore").write_text(gitignore_content)
    
    # Load the gitignore rules
    pathspec = load_gitignore(temp_dir)
    
    # Test matching against patterns
    assert pathspec.match_file("test.pyc")
    assert pathspec.match_file("__pycache__/cache.py")
    assert pathspec.match_file(".env")
    assert pathspec.match_file("dist/bundle.js")
    assert pathspec.match_file("node_modules/package.json")
    
    # Test non-matching patterns
    assert not pathspec.match_file("test.py")
    assert not pathspec.match_file("src/main.js")
    assert not pathspec.match_file("config.json")

def test_generate_file_tree(temp_dir):
    """Test generation of file tree structure with .gitignore support."""
    # Create a sample repository structure
    (temp_dir / "src").mkdir()
    (temp_dir / "src/main.py").write_text("print('hello')")
    (temp_dir / "src/test.pyc").write_text("compiled")
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__/cache.py").write_text("cache")
    (temp_dir / "README.md").write_text("# README")
    
    # Create .gitignore
    gitignore_content = """
*.pyc
__pycache__/
"""
    (temp_dir / ".gitignore").write_text(gitignore_content)
    
    # Generate tree
    pathspec = load_gitignore(temp_dir)
    tree = generate_file_tree(temp_dir, pathspec=pathspec)
    
    # Ensure the tree is split into lines correctly
    tree_lines = tree.split('\n')  # Use '\n' to split lines explicitly
    
    # Helper function to clean tree lines
    def clean_line(line):
        # Remove tree structure characters and leading/trailing whitespace
        pattern = r'^(?:(?:│ {3})| {4})*(?:├── |└── )'
        return re.sub(pattern, '', line).strip()
    
    cleaned_tree = [clean_line(line) for line in tree_lines]
    
    # Verify expected files are present and ignored files are absent
    assert "README.md" in cleaned_tree
    assert "src" in cleaned_tree
    assert "main.py" in cleaned_tree
    assert "test.pyc" not in cleaned_tree
    assert "__pycache__" not in cleaned_tree
    assert ".gitignore" in cleaned_tree

def test_traverse_folder(temp_dir):
    """Test folder traversal with .gitignore support."""
    # Create a sample repository structure
    (temp_dir / "src").mkdir()
    (temp_dir / "src/main.py").write_text("print('hello')")
    (temp_dir / "src/test.pyc").write_text("compiled")
    (temp_dir / "__pycache__").mkdir()
    (temp_dir / "__pycache__/cache.py").write_text("cache")
    (temp_dir / "README.md").write_text("# README")
    (temp_dir / ".env").write_text("SECRET=123")
    
    # Create .gitignore
    gitignore_content = """
*.pyc
__pycache__/
.env
"""
    (temp_dir / ".gitignore").write_text(gitignore_content)
    
    # Traverse folder
    pathspec = load_gitignore(temp_dir)
    files = traverse_folder(temp_dir, pathspec)
    
    # Verify traversal results
    file_paths = {file.file_path.name for file in files}
    assert "main.py" in file_paths
    assert "README.md" in file_paths
    assert "test.pyc" not in file_paths
    assert "cache.py" not in file_paths
    assert ".env" not in file_paths

def test_dump_files_to_text(temp_dir):
    """Test complete repository dumping process with .gitignore support."""
    # Create a sample repository structure
    (temp_dir / "src").mkdir()
    (temp_dir / "src/main.py").write_text("print('hello')")
    (temp_dir / "src/test.pyc").write_text("compiled")
    (temp_dir / "README.md").write_text("# README")
    (temp_dir / ".env").write_text("SECRET=123")
    
    # Create .gitignore
    gitignore_content = """
*.pyc
.env
"""
    (temp_dir / ".gitignore").write_text(gitignore_content)
    
    # Create output file
    output_file = temp_dir / "output.txt"
    
    # Dump repository
    input_data = FolderTraversalInput(
        folder_path=str(temp_dir),
        output_file=str(output_file)
    )
    dump_files_to_text(input_data)
    
    # Verify output
    content = output_file.read_text()
    assert "File Tree Structure:" in content
    assert "main.py" in content
    assert "README.md" in content
    assert "print('hello')" in content
    assert "# README" in content
    assert "test.pyc" not in content
    assert "SECRET=123" not in content

def test_git_directory_ignored(temp_dir):
    """Test that .git directory is always ignored, even without .gitignore."""
    # Create a sample repository structure with .git directory
    (temp_dir / "src").mkdir()
    (temp_dir / "src/main.py").write_text("print('hello')")
    (temp_dir / ".git").mkdir()
    (temp_dir / ".git/config").write_text("[core]\n\trepositoryformatversion = 0")
    (temp_dir / ".git/HEAD").write_text("ref: refs/heads/main")
    (temp_dir / "README.md").write_text("# README")
    
    # Create output file
    output_file = temp_dir / "output.txt"
    
    # Dump repository
    input_data = FolderTraversalInput(
        folder_path=str(temp_dir),
        output_file=str(output_file)
    )
    dump_files_to_text(input_data)
    
    # Verify output
    content = output_file.read_text()
    
    # Check that .git directory and its contents are not included
    assert ".git" not in content
    assert "config" not in content
    assert "HEAD" not in content
    assert "repositoryformatversion" not in content
    
    # Check that other files are included
    assert "main.py" in content
    assert "README.md" in content
    assert "print('hello')" in content
    assert "# README" in content

def test_markdown_without_base_folder(temp_dir):
    """Test markdown processing when no base_folder is provided."""
    # Create a nested structure
    docs_dir = temp_dir / "docs"
    docs_dir.mkdir()
    
    # Create main file in docs directory
    main_file = docs_dir / "main.md"
    main_file.write_text("""# Main File
This is a test file with a link to [[sub/other]]
""")
    
    # Create subdirectory with linked file
    sub_dir = docs_dir / "sub"
    sub_dir.mkdir()
    other_file = sub_dir / "other.md"
    other_file.write_text("""# Other File
This is another file.
""")
    
    # Create output file
    output_file = temp_dir / "output.md"
    
    # Process markdown files without specifying base_folder
    input_data = ObsidianTraversalInput(
        start_file=str(main_file),
        output_file=str(output_file)
    )
    
    dump_markdown_files(input_data)
    
    # Verify output
    content = output_file.read_text()
    
    # Check that files are included with correct relative paths
    assert "--- Start of main.md ---" in content
    assert "--- Start of sub/other.md ---" in content
    assert "# Main File" in content
    assert "# Other File" in content
    
    # Check file order and structure
    lines = content.split('\n')
    main_start_idx = lines.index("--- Start of main.md ---")
    other_start_idx = lines.index("--- Start of sub/other.md ---")
    
    # Main file should come first (it's the start file)
    assert main_start_idx < other_start_idx
    