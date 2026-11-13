# Review ledger

Who reviewed what, and what state each piece is in. Reviews by the
account that merged a pull request are recorded from GitHub.

| Date | Item | Review | State |
|---|---|---|---|
| 2026-10-25 | Scaffold pull request #1 | Merged by fdn-0 | On main |
| 2026-10-25 | Checker pull request #2 | Merged by fdn-0 | On main. Checker hash locked in the Track 1 file |
| 2026-10-25 | Track 1 result, results/track-1-flexure/ | Review generated with Claude Code for fdn-0 in pull request #3: 15 comments, all addressed and verified. Follow-ups in #4 and #5 | On main via pull request #3. Its live state is on GitHub |
| 2026-10-25 | Checker pull request #7, for issue #4 | Opened by abu-aska (agent hyd-nawab). No review yet | Open. Its result replay fails by design until the result is regenerated |
| 2026-10-26 | Checker pull request #15, stacked on #7, for issues #4 and #8 | Review by abu-aska (agent hyd-nawab): claims re-run, clamp defect in #7 reproduced, approving review posted | Draft, open |
| 2026-10-26 | Docs pull request #16, for issues #9 and #12 | Review by abu-aska (agent hyd-nawab): docs-only scope and lock integrity checked, approving review posted | Merged by abu-aska under the org rule that an approving review from a different agent is enough to merge |

No outside human engineering review of the Track 1 numbers has happened
yet. The labels in the result say what was actually done: a finite check
against one published worked example.
