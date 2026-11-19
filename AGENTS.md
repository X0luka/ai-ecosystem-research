# Project maintenance workflow

Use GitHub Flow for shared repository changes.

1. Establish the requested outcome and acceptance criteria. For requests for diagnosis or advice, report findings. Keep implementation within the requested scope. Preserve the approved research objectives and restored artifacts.
2. Start a descriptive topic branch from the current remote default branch. Isolate unrelated local changes in a separate worktree when necessary.
3. Make focused changes and run checks appropriate to the affected behavior. For reports and evidence traces, check actual content, source links and recorded outcomes. Identify gaps and report the limits of verification.
4. Inspect the exact diff for scope, private data and secrets. Stage explicit public paths, make focused commits and push the topic branch. Respect privacy exclusions and preserve unrelated history.
5. Open a pull request against the default branch. Describe the problem, changes, checks and outstanding limitations. Link an existing issue when relevant. Include visual evidence for UI changes using sanitized data.
6. Address review feedback on the topic branch and rerun affected checks. Merge through the pull request after maintainer approval and required checks pass. Verify the result and share the pull request link.

When the task includes installing a skill update, sync the validated files to the existing local installation and verify matching contents. Resolve the installation path locally.

## Default development acceptance

Before implementation, the implementing agent derives a task-specific contract from the user's outcome. In an ignored private task folder, write `plan.json` with the problem, observable success criteria, failure examples, test methods, expected evidence and limits of automation. Use the keys `problem`, `criteria`, `counterexamples`, `methods`, `evidence` and `limits`. Both criteria and methods map correctness, integration, effectiveness and regression to concrete checks. Run `python tests/quality_gate.py start FOLDER` from the repository root to freeze the contract.

For each area run `python tests/quality_gate.py run FOLDER --area AREA --artifact PATH -- COMMAND ...`. Exercise normal entry points and inject at least one fault that must fail. For integration and effectiveness, inspect actual outputs and assert against independently observable conditions. Supply the artifacts checked by the command. A test count, successful process launch, screenshot alone or agent assertion is insufficient. Keep private evidence outside version control.

After fixes rerun affected checks and verify the complete set using `python tests/quality_gate.py check FOLDER`. Changes to sources invalidate earlier receipts. Preserve the original failure condition. Mark blocked checks and unverified meaning explicitly. Include paths to real evidence and the acceptance limits in the review.

## Public and private boundaries

- Publish reusable skill instructions, scripts, tests, documentation, and explicitly sanitized examples.
- Never publish private reports, research history or evidence under `research/`, mailbox configuration, SMTP authorization codes, encrypted credential files, secrets, or personal local paths.
- Public example reports must be separately sanitized and reviewed; generating a report does not authorize publishing it.
- Private-only work stays local and does not require a public commit.
- This authorization does not include creating repositories, adding cloud scheduling, changing email delivery settings, or sending messages.
