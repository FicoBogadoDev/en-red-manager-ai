# Update Process

Use this process to keep the maintained knowledge base clean.

## Principles

- Update existing files before creating new ones.
- Create a new file only when a topic is becoming crowded or deserves its own stable home.
- Keep facts close to their best category.
- Separate intended behavior from code implementation details.
- Put chronology in `work-log.md`, not everywhere else.

## Practical Workflow

1. Decide whether the change is:
   - durable project knowledge
   - current context
   - chronological work history
   - research/report output
2. Update the right file in `docs/knowledge/` if it belongs to maintained knowledge.
3. If it is maintained knowledge, decide whether it belongs to behavior or implementation documentation.
4. Add a dated entry to `work-log.md` for meaningful work or decisions.
5. If a broader summary changed, update `project-map.md` so the folder still reads coherently.

## When To Split Files

Split a file when:

- it starts mixing multiple concerns
- one section is updated far more often than the rest
- the file becomes hard to scan quickly

## Future Skill Support

The local Codex skills in `.codex/skills/` should follow this same structure when updating docs automatically or semi-automatically.
