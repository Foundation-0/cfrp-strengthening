# Status

Tier: Seed, per the Foundation-0 Repository Standard in
Foundation-0/.github, sections A, B, and C.

## In place

- README with the question, what is known, and what is ours.
- LICENSE: MIT for code, CC BY 4.0 for text.
- NOTICE with the ACI and Simpson Strong-Tie sources and their limits.
- CONTRIBUTORS.md and CONTRIBUTING.md with claim labels and the agent
  prompt.
- Topics set: foundation-0, structural-engineering, civil-engineering,
  carbon-fiber, cfrp, concrete, aci-440.
- Branch protection on main: pull request required, 1 approval, stale
  reviews dismissed, conversations resolved, admins included, no force
  pushes, no deletions. Set 2026-10-25.

- Track 1 checker, src/flexure440.py, with input and expected files under
  tracks/track-1/ and tests under tests/. `make verify` runs the tests
  and the checker. Ten printed values from the worked example match.

## Debts, written down

- No og.jpg social image yet. The standard asks the README to open with
  one.
- No recorded result yet. The first result pull request follows the
  checker, per CONTRIBUTING.md.
- No GitHub Pages site. That is an Active tier step, and it needs a person
  to enable Pages in the repo settings.
- No pull request or issue templates yet. They arrive as the repo moves
  toward Active.
- The st0a seat for the agent doing this work, hyd-nawab, is still an open
  pull request in Foundation-0/st0a. This repo's own work does not wait on
  it, because pull requests here are signed by Shahid in the open.
