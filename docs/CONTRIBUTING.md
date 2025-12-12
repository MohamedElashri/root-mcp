# Contributing to ROOT-MCP

Thank you for your interest in contributing to ROOT-MCP! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, professional, and inclusive. We welcome contributions from everyone.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/MohamedElashri/root-mcp/issues)
2. If not, create a new issue with:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Minimal example if possible

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the feature and its use case
3. Explain why it would be useful
4. Provide examples if applicable

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/MohamedElashri/root-mcp
   cd root-mcp
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/feature-name
   ```

3. **Set up development environment**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Make your changes**
   - Write clear, readable code
   - Follow existing code style
   - Add docstrings to functions/classes
   - Update documentation if needed

5. **Add tests**
   - Write tests for new functionality
   - Ensure existing tests pass
   ```bash
   pytest tests/
   ```

6. **Run code quality checks**
   ```bash
   # Format code
   black src/

   # Lint
   ruff check src/

   # Type check
   mypy src/
   ```

7. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: brief description"
   ```

   Commit message format:
   - Use present tense ("Add feature" not "Added feature")
   - Be concise but descriptive
   - Reference issue numbers if applicable

8. **Push to your fork**
   ```bash
   git push origin feature/feature-name
   ```

9. **Open a Pull Request**
   - Describe what your PR does
   - Reference related issues
   - Include any breaking changes
   - Add screenshots if relevant

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8
- **Line Length**: 100 characters (as configured in pyproject.toml)
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Google-style docstrings

Example:
```python
def read_branches(
    path: str,
    tree_name: str,
    branches: list[str],
    selection: str | None = None,
) -> dict[str, Any]:
    """
    Read branch data from a TTree.

    Args:
        path: File path or URI
        tree_name: Name of the TTree
        branches: List of branch names to read
        selection: Optional ROOT-style cut expression

    Returns:
        Dictionary containing data and metadata

    Raises:
        KeyError: If branch doesn't exist
        ValueError: If selection syntax is invalid
    """
    # Implementation
```

### Testing

- Write tests for all new features
- Maintain or improve code coverage
- Test edge cases and error conditions
- Use pytest fixtures for common setup

Example:
```python
import pytest
from root_mcp.io import FileManager

def test_file_manager_open():
    """Test FileManager can open ROOT files."""
    manager = FileManager(config)
    file_obj = manager.open("/path/to/test.root")
    assert file_obj is not None

def test_file_manager_cache():
    """Test FileManager caching behavior."""
    manager = FileManager(config)
    file1 = manager.open("/path/to/test.root")
    file2 = manager.open("/path/to/test.root")
    assert file1 is file2  # Should be cached
```

### Documentation

- Update `../README.md` for user-facing quick start changes
- Update `ARCHITECTURE.md` for design changes
- Update `README.md` (in this folder) for documentation changes, tool reference updates, and usage examples
- Add docstrings to all public functions/classes
- Include examples in docstrings

### Commit Guidelines

Good commit messages:
- "Add histogram_2d tool for correlation analysis"
- "Fix security issue in path validation"
- "Improve caching performance by 30%"

Bad commit messages:
- "Fix bug"
- "Update code"
- "WIP"

## Project Structure

```
root-mcp/
├── src/root_mcp/
│   ├── server.py           # Main MCP server
│   ├── config.py           # Configuration
│   ├── io/                 # I/O layer
│   ├── analysis/           # Analysis operations
│   └── tools/              # MCP tool handlers
├── tests/                  # Test suite
├── examples/               # Usage examples
├── docs/                   # Documentation
└── config.yaml             # Default config
```

## Adding New Tools

To add a new MCP tool:

1. **Define the tool in the appropriate module**:
   - Discovery tools → `src/root_mcp/tools/discovery.py`
   - Data access → `src/root_mcp/tools/data_access.py`
   - Analysis → `src/root_mcp/tools/analysis.py`

2. **Add tool specification**:
   ```python
   def my_new_tool(self, param1: str, param2: int) -> dict[str, Any]:
       """
       Brief description of what the tool does.

       Args:
           param1: Description
           param2: Description

       Returns:
           Dictionary with data and metadata
       """
       # Implementation
   ```

3. **Register in server.py**:
   ```python
   Tool(
       name="my_new_tool",
       description="Description for LLMs",
       inputSchema={
           "type": "object",
           "properties": {
               "param1": {"type": "string"},
               "param2": {"type": "integer"},
           },
           "required": ["param1", "param2"],
       },
   )
   ```

4. **Add handler in call_tool()**:
   ```python
   elif name == "my_new_tool":
       result = self.analysis_tools.my_new_tool(**arguments)
   ```

5. **Write tests**:
   ```python
   def test_my_new_tool():
       """Test my_new_tool functionality."""
       # Test implementation
   ```

6. **Update documentation**:
   - Add to `docs/README.md` (tool reference + usage)

## Code Review Process

1. All PRs require review before merging
2. Address reviewer feedback promptly
3. Keep PRs focused and reasonably sized
4. Ensure CI passes before requesting review

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Tag release: `git tag -a v1.x.x -m "Release 1.x.x"`
4. Push tag: `git push origin v1.x.x`
5. GitHub Actions will build and publish to PyPI

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/MohamedElashri/root-mcp/discussions)
- **Bugs**: Open an [Issue](https://github.com/MohamedElashri/root-mcp/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
