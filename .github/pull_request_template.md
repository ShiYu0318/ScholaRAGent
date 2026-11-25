<!-- One issue per change, one commit per issue. Write in English. -->

Closes #

## What changed

<!-- The change and why, in a few lines. A table works well when one PR closes several issues. -->

## Verification

- [ ] `cd backend && uv run pytest -q`
- [ ] `cd frontend && npx tsc --noEmit && npm run build`
- [ ] `E2E=1 uv run pytest tests/e2e -q` (if the UI or an endpoint it uses changed)

## Not verified

<!-- Anything you could not check, so the reviewer knows where to look. Delete if none. -->
