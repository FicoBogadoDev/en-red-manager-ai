# Maintained Project Knowledge

This folder is the maintained documentation hub for the project.

Use it for:

- small, durable project knowledge files
- current operating context
- decisions and open questions
- the ongoing work log

Do not use it for:

- generated reports
- one-off research exports
- large transcript-derived artifacts

Those should stay under `docs/research/` or other report-specific locations.

## Structure

- `project-map.md`
  Big-picture file that ties the rest of this folder together
- `chatbot-behavior.md`
  Intended chatbot behavior, workflow rules, and operational expectations
- `implementation-architecture.md`
  Current code structure, runtime wiring, and technical reality
- `active-context.md`
  Current priorities, constraints, and open questions
- `work-log.md`
  Append-only daily log of work and decisions
- `update-process.md`
  How to maintain this folder consistently

## Maintenance Rules

- Prefer small focused files over one giant document.
- Update the smallest relevant file instead of duplicating information.
- Use `project-map.md` to connect related topics when a broader view is useful.
- Keep behavior docs and implementation docs separate, but linked.
- Treat `work-log.md` as a chronological record, not a polished summary.
- When older docs conflict with this folder, explicitly note the conflict and resolve it.
