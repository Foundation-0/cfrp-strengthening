# Status

Tier: Active, per the Foundation-0 Repository Standard in
Foundation-0/.github, sections A to D.

## In place

- README with the question, what is known, what is ours, and a results
  table.
- LICENSE: MIT for code, CC BY 4.0 for text.
- NOTICE with the ACI and Simpson Strong-Tie sources and their limits.
- CONTRIBUTORS.md and CONTRIBUTING.md with claim labels and the agent
  prompt.
- Topics set: foundation-0, structural-engineering, civil-engineering,
  carbon-fiber, cfrp, concrete, aci-440.
- Branch protection on main: pull request required, 1 approval, stale
  reviews dismissed, conversations resolved, admins included, no force
  pushes, no deletions. The CI verify jobs for Python 3.11 and 3.12 are
  required status checks. Set 2026-10-25.
- Track 1 checker, src/flexure440.py, locked by hash. Input and expected
  files under tracks/track-1/, tests under tests/.
- First result recorded: results/track-1-flexure/, with PROOF.md,
  verify.py, and certificate.json. Certificates and commitment hashes
  under certificates/ and commitment/. `make verify` replays it.
- CI in .github/workflows/verify.yml reruns every verifier and fails if
  a regenerated certificate differs from the committed one.
- Pull request and research review issue templates under .github/.
- docs/audit.md and docs/review-ledger.md state what the checks show and
  who reviewed what.
- requirements.txt: no dependencies, standard library only.

## Debts, written down

- No og.jpg social image yet. The standard asks the README to open with
  one.
- No GitHub Pages site yet. The standard places the site at the
  Published tier, and enabling Pages needs a person in the repo settings.
- The strengthened design strength in the Track 1 result is checker
  output. No printed value for it has been read yet. The obligation to
  confirm it against the publisher copy is open in the track file.
- The st0a seat for the agent doing this work, hyd-nawab, is still an
  open pull request in Foundation-0/st0a. This repo's own work does not
  wait on it, because pull requests here are signed by Shahid in the
  open.
