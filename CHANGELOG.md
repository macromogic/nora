# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-07-02

### Added

- `nora` CLI: `init`, `doctor`, `install-skill`, `update`, `help`
- `nora-project-manager` skill (short alias `/nora`) with four workflows: `new`, `reboot`, `session-update`, `sync-agents`
- `.nora/` project-state convention: `PROJECT_STATE.yaml`, `CONTEXT_BRIEF.md`, `SESSION_LOG.md`, `NEXT_ACTIONS.md`, `OPEN_LOOPS.md`
- `AGENTS.md` scaffolded into each initialized project, pointing any agent at the Nora startup protocol and human-review policy
- Skill installable into both Claude Code (`~/.claude/skills`) and Codex (`~/.codex/skills`) as symlinks, with a short `/nora` alias alongside the full skill name
- `nora update` detects changes to the `AGENTS.md` template and prompts to run `/nora sync-agents` in affected projects
- Default (argument-less, or unrecognized-argument) `/nora` invocation loads project context and responds conversationally instead of guessing a workflow
