---
name: ensure-contributing-rules
description: This skill needs to be executed, always, before a commit to the repository is done so that the proper rules are followed.
---

# ensure-contributing-rules

**TRIGGER:** Before EVERY commit to the repository.

**PURPOSE:** Ensure all contributions comply with the project's contributing guidelines (docs/contributing.md).

## Critical Rules from AGENTS.md

**BLOCKING REQUIREMENTS before any commit:**

1. **Always run pre-commit checks** via `contrib/ci.sh` (even if hooks not installed)
2. **Never commit without automated tests** - fixes/features MUST have tests
3. **Never commit without user confirmation** - ask if tested and ready
4. **Never create separate fix commits** - if tests reveal issues, fix and commit together
5. **Always document AI usage** in commit message (via `Assisted-by` tag)

## Pre-Commit Checklist

Before creating any commit, verify ALL of the following:

### 1. License Compliance

**For any new Python files:**
- [ ] File includes SPDX license identifier as the first line:
  ```python
  # SPDX-License-Identifier: GPL-3.0-or-later
  ```

**Check existing files:**
```bash
# Verify all Python files have SPDX identifier
grep -r "SPDX-License-Identifier: GPL-3.0-or-later" --include="*.py" freeipa_mcp/ tests/
```

### 2. Code Quality

**MANDATORY: Run local CI before committing:**
```bash
./contrib/ci.sh all
```

**Fix ALL issues** reported by CI before proceeding.

### 3. Testing Requirements

- [ ] New functionality includes tests
- [ ] Bug fixes include regression tests
- [ ] All tests pass (verified by CI script)

### 4. Commit Message Format

**MUST use Conventional Commits format:**

```
<type>: <short description>

[optional body]

[optional Assisted-by tag if AI was used substantially]

Signed-off-by: <Your Name> <your.email@example.com>
```

**Valid types:**
- `feat:` - new features
- `fix:` - bug fixes
- `docs:` - documentation only
- `test:` - test additions/changes
- `refactor:` - code refactoring
- `chore:` - maintenance tasks

**Examples:**

```bash
# Simple commit
git commit -s -m "feat: add user management functionality"

# With AI assistance
git commit -s -m "feat: add user management functionality

Assisted-by: Claude:claude-sonnet-4-6"

# With body and AI assistance
git commit -s -m "fix: resolve connection timeout issue

The connection timeout was caused by incorrect retry logic.
This fix implements exponential backoff.

Assisted-by: Claude:claude-sonnet-4-6"
```

### 5. Developer Certificate of Origin (DCO)

**CRITICAL:** Every commit MUST include `Signed-off-by` line.

**ALWAYS use the `-s` flag:**
```bash
git commit -s -m "your message"
```

**Verification:**
```bash
# Check last commit has sign-off
git log -1 --format=%B | grep "Signed-off-by"
```

**If missing sign-off:**
```bash
# Amend last commit (if not pushed yet)
git commit --amend -s --no-edit

# For already pushed commits - contact maintainer
```

### 6. AI Assistance Attribution

**IF you used substantial AI assistance** (Claude Code, GitHub Copilot, ChatGPT, etc.):
- [ ] Add `Assisted-by` tag to commit message
- [ ] Format: `Assisted-by: AGENT_NAME:MODEL_VERSION`
- [ ] Place BEFORE the `Signed-off-by` line

**Examples:**
```
Assisted-by: Claude:claude-sonnet-4-6
Assisted-by: GitHub-Copilot:gpt-4
Assisted-by: ChatGPT:gpt-4-turbo
```

**Note:** Basic tools (git, editors, compilers) don't need attribution.

## Commit Workflow

When the user asks to commit or you're about to commit:

1. **Run CI first:**
   ```bash
   ./contrib/ci.sh all
   ```

2. **Review changes for license headers:**
   ```bash
   git diff --name-only | grep "\.py$" | xargs -I {} sh -c 'head -1 {} | grep -q "SPDX-License-Identifier: GPL-3.0-or-later" || echo "Missing SPDX: {}"'
   ```

3. **Construct commit message:**
   - Use conventional commits format
   - Include `Assisted-by` tag (for AI assistance)
   - Always use `-s` flag for sign-off

4. **Create commit:**
   ```bash
   git commit -s -m "$(cat <<'EOF'
   <type>: <description>

   [optional body]

   Assisted-by: Claude:claude-sonnet-4-6
   EOF
   )"
   ```

5. **Verify commit:**
   ```bash
   git log -1 --format=%B
   ```

   Check for:
   - [ ] Conventional commits format (`<type>:`)
   - [ ] `Assisted-by:` tag (if applicable)
   - [ ] `Signed-off-by:` line (REQUIRED)

## Red Flags - DO NOT COMMIT IF:

**BLOCKING - these will break the build or violate policy:**
- [ ] CI script (`./contrib/ci.sh all`) fails
- [ ] New functionality lacks automated tests
- [ ] Bug fix lacks regression tests
- [ ] User has not confirmed feature is tested and ready
- [ ] New Python files missing SPDX identifier
- [ ] Commit message lacks `Signed-off-by` line
- [ ] Commit message doesn't follow conventional commits format
- [ ] Commit message lacks `Assisted-by` tag (for AI assistance)
- [ ] You haven't personally reviewed and understood all changes (especially AI-generated)
- [ ] Planning to create separate "fix" commit after feature commit (must combine)

## Quality Standards

All contributions must:
- Pass all tests
- Pass all CI checks
- Follow project style and conventions
- Include appropriate tests for new functionality
- Be personally reviewed and understood by the contributor

## Notes

**From AGENTS.md - Critical Requirements:**
- **ALWAYS run pre-commit checks** via `contrib/ci.sh` (even if hooks not installed)
- **NEVER commit without automated tests** for the feature/fix
- **NEVER commit without asking user** if tested and ready
- **NEVER separate commits** for feature and its fixes (combine into one)
- **ALWAYS document AI usage** via `Assisted-by` tag

**From Contributing Guide:**
- The `Signed-off-by` line is YOUR personal certification of submission rights
- AI assistance is permitted, but YOU are fully responsible for quality
- Run `./contrib/ci.sh all` locally to catch issues before pushing
- Keep commits focused - one feature or fix per commit
- Force push is acceptable when addressing review feedback

**Pull Request Policy:**
- If tests reveal issues with a feature during development, fix them BEFORE committing
- Never allow a PR with "add feature X" + "fix feature X" commits
- The feature should be complete and tested in a single commit

## When User Asks to Commit

**MANDATORY workflow - follow in order:**

1. **Verify tests exist:**
   - New features MUST have tests
   - Bug fixes MUST have regression tests
   - If no tests exist, STOP and create tests first

2. **Run CI checks:**
   ```bash
   ./contrib/ci.sh all
   ```
   - If CI fails, STOP and fix issues
   - If fixes are needed, they go in SAME commit (not separate)

3. **Check SPDX identifiers:**
   ```bash
   git diff --name-only | grep "\.py$" | xargs -I {} sh -c 'head -1 {} | grep -q "SPDX-License-Identifier: GPL-3.0-or-later" || echo "Missing SPDX: {}"'
   ```

4. **Review changes:**
   - Run `git status` and `git diff`
   - Ensure you understand all changes

5. **ASK USER FOR CONFIRMATION:**
   > "The changes have passed CI checks. Have you tested the feature/fix and is it ready to commit?"

   **DO NOT PROCEED without user confirmation**

6. **Only after user confirms - construct commit:**
   ```bash
   git commit -s -m "$(cat <<'EOF'
   <type>: <description>

   [optional body]

   Assisted-by: Claude:claude-sonnet-4-6
   EOF
   )"
   ```

7. **Verify commit message:**
   ```bash
   git log -1 --format=%B
   ```

## Blocking Requirements - NEVER Commit Without

- [ ] Automated tests for the feature/fix
- [ ] CI checks passing (`./contrib/ci.sh all`)
- [ ] User confirmation that feature is tested and ready
- [ ] SPDX identifiers on new Python files
- [ ] Sign-off via `-s` flag
- [ ] Conventional commits format
- [ ] AI attribution (`Assisted-by` tag)

## Special Cases

**If tests reveal issues during CI run:**
- Fix the issues
- Re-run CI to verify fixes
- Commit feature AND fixes together (single commit)
- NEVER create separate commits for "fix feature X" after "add feature X"
