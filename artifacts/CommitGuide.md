# Commit Message Guide

> **Version History**
>
> - 2025‑12‑10 – v1.1 – Aligned with Conventional Commits, clarified branch/tag naming, and linked commit practices to versioning and release metadata.
> - 2025‑11‑xx – v1.0 – Initial version prior to control‑doc consolidation.

---

This project uses **Conventional Commits**. Husky + commitlint will reject messages that don’t follow this format.

## Basic Format

```text
<type>(optional-scope): <short description>
```

- All lowercase for the `<type>` and scope.
- Use imperative mood for the description (e.g., “add login screen”, not “added login screen”).

## Common Types

- `feat` – New features or user-visible behavior.
- `fix` – Bug fixes.
- `style` – Visual/UI-only changes (CSS/layout) with no behavior changes.
- `refactor` – Code changes that are not bug fixes or features.
- `docs` – Documentation changes (README, specs, etc.).
- `test` – Adding or updating tests.
- `chore` – Build tools, configs, or other non-product code changes.

## Examples for This Repo

- `feat(web): add cinematic login screen`
- `feat(web): implement mocked localization workspace`
- `style(workspace): stack controls and refine language selector`
- `refactor(services): simplify mock localization pipeline`
- `docs(artifacts): update sprint 1 notes`

## Tips

- Keep descriptions short but specific.
- Group related changes into one commit instead of many tiny commits.
- If a commit touches multiple areas, choose the most representative scope or omit the scope entirely.
