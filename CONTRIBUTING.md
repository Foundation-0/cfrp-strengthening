# Contributing

This project turns ACI 440.2R-17 design checks into small programs that
anyone can re-run. Work runs in tracks. Each track has one worked example
as its test set and one checker as its judge.

## The loop

1. Pick a track in tracks/ and read its file, including the failed attempts
   and the open obligations.
2. Fork, branch, and work on that branch.
3. A checker judges every result. The checker for a track is locked: its
   sha256 hash is recorded in the track file, and a pull request that edits
   a checker is reviewed on its own, never in the same pull request as a
   result.
4. Open one pull request per result. Include the input file, the checker
   output, the exact command to reproduce it, what you tried that did not
   work, and the prior sources you checked.
5. Never merge your own result. A person who did not write it reviews and
   merges it.

## Claim labels

- PROVEN: a written proof or a full derivation from stated inputs, open to
  read.
- VERIFIED: a finite check ran and matched. Say what it matched, for
  example a published worked example. A finite check is not a proof.
- KNOWN: cited to a source. Name the source.
- CONJECTURE: believed, not yet checked. Say what check would settle it.

A search that finds nothing means "not found in the searches listed". It
never means "new".

## Rules

- Credit every method, example, and person you build on. Keep licences.
  List new sources in NOTICE before code that uses them lands.
- Disclose AI assistance and name the model in every pull request.
- No hype. Exact statements, honest limits.
- Engineering limits stay visible. A checker output is a calculation aid.
  It is not a design, and it does not replace the engineer of record or the
  full ACI guide.

## Agent prompt

Paste this into an agent from inside your fork:

```
Read README.md, CONTRIBUTING.md, and tracks/README.md. Pick one open
track and read its track file in full, including failed attempts and open
obligations. Reproduce the current state first: if a checker exists, run
it on the track input file and record the output. Work only on inputs,
notes, or result files. Never edit a locked checker in the same change as
a result. Label every claim PROVEN, VERIFIED, KNOWN, or CONJECTURE. When
you have a checker-matched result, prepare one pull request with the input
file, the checker output, the exact reproduction command, the failed
attempts, and the sources you checked. Do not merge, and do not claim
the result is new.
```
