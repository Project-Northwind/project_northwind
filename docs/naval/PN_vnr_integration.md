# Project Northwind naval integration

Source: installed Workshop 2993766165, VNR v3.3 - Das Boot. Original author: MrPunk. See `PN_naval_baseline.json` for the immutable source hashes and original 139 Northwind ships / 152 country-history naval variant blocks.

## Execution ledger

Plan: `docs/superpowers/plans/2026-10-20-vnr-integration.md`. Native execution approved by the user.

- Ruling: Work in the existing `VNR-Fix` branch and installed Northwind directory. The user requested native execution in this project; this keeps the launcher path valid and avoids an unrequested checkout relocation. Changes are protected by staged checkpoints and the immutable baseline.
- Preflight: Task 1 baseline feeds Tasks 2–5; Task 2 path manifest feeds Tasks 3–5; Task 3 owner/class mapping feeds Task 4 startup and Task 5 runtime checks. Preserve these interfaces as recorded JSON, rather than transient in-memory state.
- Task 1: Parser tests first failed because the validator did not exist. Initial implementation exposed compact `{}` tokenization; corrected lexer to tokenize braces individually. Five validator unit tests now pass.
- Baseline logs already contain unrelated Northwind government/decision errors. Do not attribute those to the naval port or erase them to manufacture a clean result.

## Naming

Imported additive files use `PN_`; exact base-game overrides retain their required relative paths. Each file, hash, destination and exception is recorded in `PN_vnr_import_manifest.json`. Original equipment/module/technology IDs remain compatibility identifiers. New integration logic follows Northwind naming.

## Validation

Run `python -m unittest discover -s tests -p test_PN_naval_validation.py` and `python tools/PN_validate_naval.py` from the project root. Runtime verification is recorded separately and must not be inferred from static checks.
