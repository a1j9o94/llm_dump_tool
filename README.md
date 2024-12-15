# LLM Dump Tool

A versatile Python tool for dumping repository contents and markdown files into a single file, making it easier to provide context to Large Language Models (LLMs).

## Features

- **Git Repository Dump**
  - Dumps entire repository contents while respecting `.gitignore` rules
  - Generates a visual file tree structure
  - Automatically excludes `.git` directory and binary files
  - Preserves file structure in output

- **Markdown/Obsidian Processing**
  - Traverses markdown files following both wiki-style and standard markdown links
  - Supports Obsidian-style `[[wiki links]]` and standard `[markdown](links)`
  - Configurable traversal depth
  - Handles relative paths and nested directories
  - Preserves link relationships between files

## Installation

```bash
pip install llm-dump-tool
```

## Usage

### Git Repository Dump

Dump the contents of a Git repository to a single file:

```bash
python -m llm_dump git /path/to/repository output.txt
```

### Markdown/Obsidian Processing

Process markdown files starting from a specific file:

```bash
python -m llm_dump markdown /path/to/start.md output.txt --max-depth 2 --base-folder /path/to/base
```

#### Options:
- `--max-depth`: Maximum depth to traverse linked files (default: 2)
- `--base-folder`: Base folder for resolving links (default: start file's folder)

## Output Format

### Git Repository Output
The output file contains:
1. A visual tree structure of the repository
2. Contents of each file, clearly marked with start/end markers
3. Relative paths preserved

Example:
```
File Tree Structure:
├── src
│   ├── main.py
│   └── utils.py
└── README.md

--- Start of src/main.py ---
def main():
    print("Hello World")
--- End of src/main.py ---

...
```

### Markdown Output
The output file contains:
1. Contents of the starting file
2. Contents of all linked files (up to max depth)
3. Clear markers indicating file boundaries

Example:
```
--- Start of main.md ---
# Main Document
[[linked-doc]]
--- End of main.md ---

--- Start of linked-doc.md ---
# Linked Document
Content here...
--- End of linked-doc.md ---
```

## Development

### Requirements
- Python 3.8+
- pathspec
- pydantic

### Running Tests
```bash
pytest test_llm_dump.py -v
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
