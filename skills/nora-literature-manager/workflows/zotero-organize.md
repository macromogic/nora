# Authorized Zotero organization

Read [zotero-review.md](zotero-review.md) for scope and classification rules. Use `nora zotero help` and subcommand help for the installed CLI's exact syntax.

1. Reconstruct the concrete approved plan from the conversation or saved proposal. Existing authorization persists: execute approved entries without asking again. Partial approval covers only the selected entries; later corrections replace the affected pending actions. Clarify only unresolved choices needed for a mutation. Save stable keys with titles rather than relying on numbered lists alone.
2. Obtain current previews for the approved operations. Configuration flags precede the `nora zotero` subcommand. Apply with the reviewed `--expect-library-version`; after each write, obtain a fresh preview/version for the next operation. Never substitute a new version blindly after a conflict.
3. Preserve operation semantics:
   - `collection create` creates a destination; `collection edit` renames/reparents a collection while preserving its key.
   - `collection add-items` is additive. `--finish-inbox` also removes inbox memberships; `--flatten-inbox` consolidates inbox descendants into the root. Use these only when the approved plan calls for those removals.
   - `item trash` moves a top-level bibliographic item to the recoverable Zotero Trash. It is not permanent deletion. Restoration currently uses Zotero itself.
   - `collection delete-empty` removes an empty leaf. A scoped report showing zero items is insufficient: ignored or trashed members can prevent deletion. Leave such collections untouched and report the reason.
4. On an error or uncertain write outcome, inspect the operation journal and current remote state before retrying. Do not replay a whole batch or infer rollback. Reconcile completed operations with the approved plan; stop dependent actions if their prerequisites are uncertain. Do not change credentials or widen scope to make a failed operation pass.
5. Check read-back results and refresh with `audit --write` after the batch. If refresh fails, report completed writes separately from the stale local snapshot. Offline import/sync apply is blocked when local write journals establish stale or uncertain state; a fresh online snapshot is the normal recovery path.

Report applied, failed/uncertain, skipped, and still-undecided changes, together with the verified library version and snapshot freshness. Preserve other memberships and tags unless explicitly included in the approved plan. A temporary script is not a native resumable batch feature; do not promise atomic multi-command execution or automatic undo.
