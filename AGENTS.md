# Project maintenance workflow

The repository owner authorizes the following default workflow for this project:

1. Make the requested changes and run checks appropriate to the change.
2. Review the exact diff for private data and secrets. Stage explicit public paths; never use force-add to bypass privacy exclusions.
3. Sync validated skill changes to the existing local installation and verify matching file contents. Resolve the installation path in the current environment; do not hardcode a user directory into the skill.
4. Commit the completed changes and push to the existing configured GitHub remote without asking again. Confirm the remote commit and provide its link.
5. If checks fail or a push is rejected, resolve the cause safely; do not force-push, overwrite unrelated changes, or claim success without verification.

## Public and private boundaries

- Publish reusable skill instructions, scripts, tests, documentation, and explicitly sanitized examples.
- Never publish private reports, research history or evidence under `research/`, mailbox configuration, SMTP authorization codes, encrypted credential files, secrets, or personal local paths.
- Public example reports must be separately sanitized and reviewed; generating a report does not authorize publishing it.
- Private-only work stays local and does not require a public commit.
- This authorization does not include creating repositories, adding cloud scheduling, changing email delivery settings, or sending messages.
