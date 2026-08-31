# git-distill ⚗️

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Type Checked](https://img.shields.io/badge/types-mypy-blueviolet.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Selective Git branch release triage and restore CLI.**  
> Distill pure, deployable changes from mixed feature/staging branches before deployment.

---

## 🎯 The Problem

In shared monorepo and multi-developer Git workflows (`feature/*` ➔ `dev` ➔ `test` ➔ `prod`), multiple authors push commits concurrently to prepare a release. During release reviews or Change Advisory Board (CAB) gates, only a subset of features or authors are approved for deployment.

When some authors' changes are not ready to ship, release leads face high friction:
- **Divergence Confusion**: Identifying which commits and files belong to unconfirmed vs. confirmed authors across long commit histories is difficult and error-prone.
- **Mixed Files**: Simple file-level reverts break when a single file mixes approved changes with unapproved changes at the line or hunk level.
- **Cherry-picking Risks**: Manual cherry-picking or interactive rebasing risks introducing merge regressions, losing work, or accidentally promoting unready bugs into production.

---

## ⚡ The Solution

**`git-distill`** runs directly on your local branch as an authoritative release preparation and triage tool:

1. 🔍 **Discovers** all unmerged commits and file divergences against the baseline (`origin/prod`, `main`, or custom target) using native `git merge-base` and `git diff`.
2. 🏷️ **Classifies** files into **Pure Confirmed** (keep), **Pure Unready** (restore to baseline), or **Mixed** (interactive review).
3. ⚡ **Restores** 100% unready files back to the exact baseline state in one atomic step, deleting unready newly created files.
4. 🔀 **Launches Visual Diff UI** (`code --wait --diff` or custom editor) for mixed files, enabling precise hunk-level resolution.
5. 🛡️ **Protects** release leads with automatic pre-restore backup branches (`backup/<branch>-<timestamp>`), dry-run simulations, one-command rollback (`undo`), and structured Markdown/JSON audit trails.

Once distilled, the branch merges cleanly into your target release pipeline.

---

## 🚀 Key Features

- 🔍 **Discovery & Divergence Mapping**: Computes merge-base, summarizes commits, diffstat (+/- lines), and maps contributing authors per touched file.
- 🛡️ **Branch Guard**: Strict validation preventing accidental execution on `prod`, `main`, `master`, `dev`, or `test` branches.
- ⚡ **Surgical Baseline Restore**: Automatically checks out baseline versions for unready files and removes unready additions.
- 🔀 **Visual Diff / Merge Editor Integration**: Launches VS Code side-by-side diff view with the exact baseline snapshot for mixed files.
- ⏪ **One-Command Undo**: Instantly rolls back the branch to the pre-restore snapshot with `git-distill undo` (or `git distill undo`).
- 📝 **Structured Audit Logs**: Automatically saves JSON (`.gitdistill/audit-<timestamp>.json`) and human-readable Markdown (`.gitdistill/audit-<timestamp>.md`) logs.
- 💬 **Standardized Revert Commits**: Automatically commits changes with conventional commit metadata (`revert(silver-bullet): ...`).
- 🔌 **Native Git Subcommand**: Installs as both `git-distill` and `gitdistill` so you can use standard `git distill <cmd>` syntax.

---

## 📦 Installation

### Requirements
- Python 3.9+
- Git 2.30+
- VS Code (optional, for visual side-by-side diff editor)

### Install via pip / pipx
```bash
# Clone the repository
git clone https://github.com/<your-username>/git-distill.git
cd git-distill

# Install using pip in editable mode
pip install -e .

# Or install globally via pipx
pipx install .
```

---

## 🛠️ Typical Workflow: Release Triage

### 1. Checkout Your Feature/Staging Branch
```bash
git checkout feature/checkout-v2
```

### 2. Discover Unmerged Work
Inspect all unmerged commits, authors, and modified files compared to production:
```bash
git distill scan
```

### 3. Review & Classify with Confirmations
Filter by confirmed and unready authors:
```bash
git distill review --confirmed "Alice Miller" --unready "Bob Vance"
```

### 4. Preview with Dry Run
Simulate the restore plan without altering the working tree or Git state:
```bash
git distill restore --confirmed "Alice Miller" --unready "Bob Vance" --dry-run
```

### 5. Execute Restore & Resolve Mixed Diffs
Run the distillation operation. `git-distill` automatically:
- Creates safety backup branch `backup/feature/checkout-v2-YYYYMMDD_HHMMSS`
- Restores 100% unready files back to baseline state
- Opens VS Code Diff UI for mixed files so you can keep ready hunks and discard unready lines
- Stages resolved files and creates an atomic Git commit
- Generates JSON and Markdown audit logs under `.gitdistill/`

```bash
git distill restore --confirmed "Alice Miller" --unready "Bob Vance"
```

### 6. (Optional) Rollback
If you need to revert the entire operation back to the pre-restore state:
```bash
git distill undo
```

---

## 📖 Command Reference

You can invoke commands either as `git distill <command>`, `git-distill <command>`, or `gitdistill <command>`.

### `scan`
Scans the current feature branch against the production baseline and renders an executive report.

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--prod-branch` | `-p` | Baseline production branch reference | Auto-detected (`prod`, `main`, `master`) |
| `--confirmed` | `-c` | Comma-separated list of confirmed authors | `None` |
| `--unready` | `-u` | Comma-separated list of unready authors | `None` |
| `--confirmed-files` | | Comma-separated list of confirmed file paths | `None` |
| `--unready-files` | | Comma-separated list of unready file paths | `None` |
| `--bypass-branch-check` | `--force` | Bypass `feature/*` branch safety guard | `False` |

---

### `review`
Interactively preview and verify classification status for all touched files.

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--prod-branch` | `-p` | Baseline production branch reference | Auto-detected (`prod`, `main`, `master`) |
| `--confirmed` | `-c` | Comma-separated list of confirmed authors | `None` |
| `--unready` | `-u` | Comma-separated list of unready authors | `None` |
| `--confirmed-files` | | Comma-separated list of confirmed file paths | `None` |
| `--unready-files` | | Comma-separated list of unready file paths | `None` |
| `--bypass-branch-check` | `--force` | Bypass `feature/*` branch safety guard | `False` |

---

### `restore`
Executes full restoration of unready files, opens diff editor for mixed files, and commits the result.

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--prod-branch` | `-p` | Baseline production branch reference | Auto-detected (`prod`, `main`, `master`) |
| `--confirmed` | `-c` | Comma-separated list of confirmed authors | `None` |
| `--unready` | `-u` | Comma-separated list of unready authors | `None` |
| `--confirmed-files` | | Comma-separated list of confirmed file paths | `None` |
| `--unready-files` | | Comma-separated list of unready file paths | `None` |
| `--diff-editor` | | Custom diff editor command (e.g. `code --wait --diff`) | `None` |
| `--dry-run` | `-n` | Preview planned actions without modifying filesystem | `False` |
| `--bypass-branch-check` | `--force` | Bypass `feature/*` branch safety guard | `False` |

---

### `undo`
Safely resets `HEAD` and working directory to the most recent pre-restore backup branch snapshot.

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--yes` | `-y` | Confirm rollback without interactive prompt | `False` |
| `--bypass-branch-check` | `--force` | Bypass `feature/*` branch safety guard | `False` |

---

## ⚙️ Environment Variables

- `GITDISTILL_DIFF_EDITOR`: Override default diff editor command (defaults to `code --wait --diff`).

---

## 🧪 Development & Testing

```bash
# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies in editable mode
pip install -e .
pip install pytest mypy

# Run the test suite
pytest -v

# Run type checker
mypy src
```

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
