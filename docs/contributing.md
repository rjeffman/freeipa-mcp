# Contributing to freeipa-mcp-py

Thank you for your interest in contributing to this project. This guide outlines the process for submitting contributions.

## Licensing and Sign-off

### License

This project is released under the **GNU General Public License v3.0 or later (GPLv3+)**. All source code files must include an SPDX License Identifier:

```python
# SPDX-License-Identifier: GPL-3.0-or-later
```

By contributing to this project, you agree that your contributions will be licensed under the same terms.

### Developer Certificate of Origin

This project uses a [Developer Certificate of Origin (DCO)]() rather than a Contributor License Agreement (CLA). Every commit must include a `Signed-off-by` line to certify that you have the right to submit the code.

Add the sign-off with the `--signoff` or `-s` flag:

```bash
git commit -s -m "Your commit message"
```

This adds a trailer to your commit message:

```
Signed-off-by: Your Name <your.email@example.com>
```

By signing off, you certify that:

1. The contribution was created in whole or in part by you and you have the right to submit it under the project's license; or
2. The contribution is based upon previous work that, to the best of your knowledge, is covered under an appropriate license and you have the right under that license to submit that work with modifications; or
3. The contribution was provided directly to you by someone who certified (1) or (2) and you have not modified it.

**Important**: Commits without a `Signed-off-by` line will not be accepted.

If your employer has rights to intellectual property you create, verify that you have permission to contribute to open source projects before submitting.

### AI-Assisted Contributions

This project permits the use of AI coding assistants (such as GitHub Copilot, Claude, ChatGPT, etc.) with the following requirements:

#### 1. Personal Responsibility

You must personally review, understand, and test all AI-generated code or documentation. You are fully responsible for the quality and correctness of your submission, regardless of how it was created. Submitting AI-generated content that you have not reviewed and understood is not acceptable.

#### 2. Developer Certificate of Origin Still Applies

The `Signed-off-by` line certifies that you understand and have the right to submit the contribution. This certification is your personal attestation, regardless of whether AI tools were involved in creating the code.

#### 3. Quality Standards

AI-generated contributions must meet the same quality standards as human-written code:
- Code must pass all tests
- Code must pass the CI checks (run `contrib/ci.sh all` locally)
- Code must follow the project's style and conventions
- Commits must include appropriate tests for new functionality

#### 4. Attribution

For contributions with substantial AI assistance, add an `Assisted-by` tag to your commit message following the Linux Kernel attribution format:

```
Your commit message here

Assisted-by: AGENT_NAME:MODEL_VERSION

Signed-off-by: Your Name <your.email@example.com>
```

**Examples:**
```
Assisted-by: Claude:claude-sonnet-4-6
Assisted-by: GitHub-Copilot:gpt-4
Assisted-by: ChatGPT:gpt-4-turbo
```

**Notes:**
- The `Assisted-by` tag should include the AI system name and model version
- Do not include basic development tools (git, editors, compilers) in the attribution
- Use your judgment on what constitutes "substantial" assistance—a brief note is sufficient
- The goal is transparency, not restriction

## Contribution Workflow

### 1. Fork and Clone

Fork the repository on GitHub and clone your fork:

```bash
git clone https://github.com/YOUR-USERNAME/freeipa-mcp-py.git
cd freeipa-mcp-py
git remote add upstream https://github.com/rjeffman/freeipa-mcp-py.git
```

### 2. Create a Branch

Create a feature branch from the latest `main`:

```bash
git fetch upstream
git checkout -b feature/your-feature-name upstream/main
```

Use descriptive branch names:
- `feature/add-user-management`
- `fix/connection-timeout`
- `docs/improve-readme`

### 3. Make Changes

- Make focused, logical commits
- Include tests for new functionality or bug fixes
- Update documentation as needed
- Follow existing code style and conventions

### 4. Run Local CI

Before committing, run the local CI script to ensure your changes pass all checks:

```bash
./contrib/ci.sh all
```

Fix any issues reported by the CI script.

### 5. Commit with Sign-off

Commit your changes with the required sign-off:

```bash
git commit -s -m "feat: add user management functionality"
```

If you used AI assistance substantially, include the `Assisted-by` tag:

```bash
git commit -s -m "feat: add user management functionality

Assisted-by: Claude:claude-sonnet-4-6"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/) format for commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions or changes
- `refactor:` for code refactoring
- `chore:` for maintenance tasks

### 6. Push and Create Pull Request

Push your branch to your fork:

```bash
git push origin feature/your-feature-name
```

Open a pull request against `rjeffman/freeipa-mcp-py:main` on GitHub.

In your PR description:
- Explain what the change does and why
- Reference any related issues (e.g., "Fixes #123")
- Note if AI assistance was used (brief transparency note)
- List any breaking changes or special considerations

### 7. Address Review Feedback

- Push additional commits to address review comments. Force push is acceptable.
- Respond to reviewer comments
- Maintainers will merge your PR once it's approved and CI passes

## Best Practices

- **Keep PRs focused**: One feature or fix per PR. Don't bundle unrelated changes.
- **Write tests**: New features and bug fixes should include tests.
- **Document your code**: Add docstrings and update documentation as needed.
- **Run CI locally**: Catch issues before pushing with `./contrib/ci.sh all`.
- **Communicate**: If you're working on something significant, consider opening an issue first to discuss the approach.

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Reach out to the maintainers

Thank you for contributing to freeipa-mcp-py!
