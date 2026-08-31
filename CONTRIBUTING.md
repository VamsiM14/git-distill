# Contributing to git-distill

Thank you for your interest in contributing to **git-distill**! 🎉

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/git-distill.git
   cd git-distill
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install in editable mode with development dependencies:**
   ```bash
   pip install -e .
   pip install pytest mypy
   ```

4. **Run the test suite:**
   ```bash
   pytest
   ```

## Pull Request Guidelines

- Ensure all existing and new unit tests pass (`pytest`).
- Maintain type hints and clean formatting.
- Include descriptive commit messages following Conventional Commits (e.g. `feat:`, `fix:`, `docs:`, `test:`).
- Document new flags or CLI behaviors in `README.md`.
