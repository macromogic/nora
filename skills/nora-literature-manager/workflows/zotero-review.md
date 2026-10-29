# Zotero library review

Use this workflow for library inspection and organization proposals, without initializing a project.

1. Resolve the intended library and explicitly selected credential source. Report the library identity and source path, never credential values. `doctor` verifies read access only; do not infer write permission.
2. Apply the shared skill's default collection rules and read `nora zotero ignore list` for additional exclusions. Ignoring underscore-prefixed collections except `_inbox` and avoiding venue-based classification are general rules, not per-library preferences. Other user-specific taxonomy choices belong in persistent user/library context; do not invent an unsupported preferences command.
3. Use `audit --write` when a current saved review is needed; read its compact report first. Offline results describe a saved version, not necessarily the live library. Surface freshness warnings. Trashed items and their children are excluded from active analysis in newly fetched snapshots; old snapshots may need a refresh.
4. Ground classification in available abstracts, notes, and user research goals. State when only a title is available. Classify by topic, problem, or project; do not propose venue collections or venue/year inbox subdivisions. Preserve venue metadata and distinguish publication versions; duplicate DOI/title findings are not automatic merge instructions. Allow multiple collections and leave uncertain items in an agreed inbox. Create a collection only when it serves a clear retrieval need.
5. Present concrete proposed changes with stable item/collection keys, titles, old and target memberships, evidence, and unresolved questions. Distinguish additive membership from removing inbox membership and trashing an item. Respect existing taxonomy and the user's scope; inspecting collections does not authorize editing tags.

If full text returns 403, explain the evidence gap and offer manual download or a Zotero attachment as a continuation. Read a supplied local file with available tools; do not claim the CLI transfers attachments or bypass access controls.

End with the snapshot version/time, actionable proposals, and uncertainty. Library organization does not promote project papers to read/cited states. Use the project decision gate only for the project research changes it governs.
