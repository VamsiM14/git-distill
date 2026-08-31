# Security Policy

## 🔒 Security & Privacy Guarantees

**`git-distill` is built with a zero-telemetry, offline-first security architecture.**

### 1. Zero Telemetry & Snooping
- **No Remote Tracking**: `git-distill` contains zero analytics, tracking beacons, telemetry, or external API endpoints.
- **Zero Third-Party Network Dependencies**: `git-distill` does not import network libraries (`requests`, `urllib`, `httpx`, `aiohttp`, etc.).
- **Air-Gapped Friendly**: All operations run locally against the checked-out repository. Remote branch references are fetched via standard `git fetch` only when an `origin` remote exists, and can be completely suppressed with the `--no-fetch` / `--offline` flag.

### 2. Local-Only Audit Trail
- All audit logs are written exclusively to the local `.gitdistill/` folder within your working directory.
- The `.gitdistill/` directory is gitignored by default to prevent accidental commits of local session logs.
- You can disable audit logging entirely using `--no-audit` or scrub existing logs with `git distill audit --clean`.

### 3. Safe Subprocess Execution
- All Git operations are executed through structured argument vectors (`subprocess.run([git_bin, ...])`) with `shell=False` to prevent command injection vulnerabilities.
- Binaries are validated via `shutil.which` before execution.

---

## 🛡️ Automated Security Scanning in CI

Every pull request and release is validated through:
- **Bandit**: Static AST security analysis for Python code safety.
- **pip-audit**: Continuous dependency vulnerability & CVE scanning.
- **GitHub CodeQL**: Automated semantic code analysis for security vulnerabilities.
- **Dependabot**: Automated security updates for project dependencies.

---

## 📬 Reporting a Vulnerability

If you discover a security vulnerability within `git-distill`, please submit a report via GitHub Private Vulnerability Reporting or open a security advisory. We review and respond to reports promptly.
