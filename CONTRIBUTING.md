# Contributing

Two rules protect this repository's structure; everything else is ordinary.

## Per-path licensing

Grants are per-directory (see the root LICENSE map). A contribution is made
under the license of the directory it lands in. Do not move files across
license boundaries in the same change that modifies them.

## agent/ contributions require a CLA

The (future) agent/ directory is planned as AGPL-3.0 with dual-licensing
optionality retained by the maintainer. To preserve that option, contributions
to agent/ will require a contributor license agreement assigning or broadly
licensing the contribution to the maintainer. This clause exists from day one
so it never has to be retrofitted across a contributor history.

## Structural rules

- Skills are dependency-free: nothing outside a skill's folder may be required
  at runtime. Agent tooling never leaks into skills/.
- conventions/ is canonical. Skills carry mirrors in references/ with a
  synced-from header; a mirror that drifts from canonical is a defect, and the
  fix flows canonical -> mirror, never the reverse.
- Every skill upholds the standalone invariant (interaction-grammar.md §1).
- Every skill folder carries its own LICENSE copy, so packaged .skill files
  and zips remain self-describing when they travel detached from the repo.
