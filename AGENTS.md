# Project maintenance workflow

Use GitHub Flow for shared repository changes.

1. Establish the requested outcome and acceptance criteria. For requests for diagnosis or advice, report findings. Keep implementation within the requested scope. Preserve the approved research objectives and restored artifacts.
2. Start a descriptive topic branch from the current remote default branch. Isolate unrelated local changes in a separate worktree when necessary.
3. Make focused changes and run checks appropriate to the affected behavior. For reports and evidence traces, check actual content, source links and recorded outcomes. Identify gaps and report the limits of verification.
4. Inspect the exact diff for scope, private data and secrets. Stage explicit public paths, make focused commits and push the topic branch. Respect privacy exclusions and preserve unrelated history.
5. Open a pull request against the default branch. Describe the problem, changes, checks and outstanding limitations. Link an existing issue when relevant. Include visual evidence for UI changes using sanitized data.
6. Address review feedback on the topic branch and rerun affected checks. Merge through the pull request after maintainer approval and required checks pass. Verify the result and share the pull request link.

When the task includes installing a skill update, sync the validated files to the existing local installation and verify matching contents. Resolve the installation path locally.

## Public and private boundaries

- Publish reusable skill instructions, scripts, tests, documentation, and explicitly sanitized examples.
- Never publish private reports, research history or evidence under `research/`, mailbox configuration, SMTP authorization codes, encrypted credential files, secrets, or personal local paths.
- Public example reports must be separately sanitized and reviewed; generating a report does not authorize publishing it.
- Private-only work stays local and does not require a public commit.
- This authorization does not include creating repositories, adding cloud scheduling, changing email delivery settings, or sending messages.
