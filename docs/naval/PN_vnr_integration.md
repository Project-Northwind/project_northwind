# Project Northwind naval integration

Source: installed Workshop 2993766165, VNR v3.3 - Das Boot. Original author: MrPunk. See `PN_naval_baseline.json` for the immutable source hashes and original 139 Northwind ships / 152 country-history naval variant blocks.

## Execution ledger

Plan: `docs/superpowers/plans/2026-10-20-vnr-integration.md`. Native execution approved by the user.

- Ruling: Work in the existing `VNR-Fix` branch and installed Northwind directory. The user requested native execution in this project; this keeps the launcher path valid and avoids an unrequested checkout relocation. Changes are protected by staged checkpoints and the immutable baseline.
- Preflight: Task 1 baseline feeds Tasks 2–5; Task 2 path manifest feeds Tasks 3–5; Task 3 owner/class mapping feeds Task 4 startup and Task 5 runtime checks. Preserve these interfaces as recorded JSON, rather than transient in-memory state.
- Task 1: Parser tests first failed because the validator did not exist. Initial implementation exposed compact `{}` tokenization; corrected lexer to tokenize braces individually. Five validator unit tests now pass.
- Baseline logs already contain unrelated Northwind government/decision errors. Do not attribute those to the naval port or erase them to manufacture a clean result.
- Task 1: complete — baseline committed as `4f332c4`; tests cover script structure, repeated keys, missing hull/module references and owner/class resolution.
- Ruling: The baseline's five reported source syntax issues were lexer false positives for adjacent braces, not source defects. The corrected lexer finds no unmatched source braces; source hashes and original ship inventory remain immutable.
- Ruling: Northwind filename prefixes alter HOI4 dependency ordering. Consolidate naval equipment into `PN_naval_equipment.txt` in original source order, with exact-path vanilla suppression files; retain the original late-loading `x_plane_airframes.txt` because it duplicates aircraft archetypes defined earlier by the engine.
- Ruling: Merge static modifiers, carrier-airwing units, entity clones and special-project overrides into required original files. Additive duplicates produce runtime errors or lose the intended overrides. Each exception is in the import manifest.
- Ruling: Suppress the inherited 1939 bookmark. The source supports fresh 1936 starts, and silently exposing an unconverted 1939 scenario would misrepresent support.
- Task 2: imported 1,649 source files, retaining Northwind identity and credits. Thirty missing or stale source art references now point to existing VNR/base-game assets; their substitutions are recorded in the manifest.
- Task 3: converted 152 Northwind history design blocks, preserved 139 ships and 12 shipyard orders, and converted 202 inherited naval reward design blocks plus their equipment references. Preserve original date/DLC gates through Northwind-named scripted effects.
- Ruling: Retain nonbuildable legacy equipment and hidden technology compatibility IDs used by inherited history/events. Active starting fleets, production and converted rewards use VNR hulls; removing the old IDs causes database errors even when their content is hidden.
- Ruling: The inherited ice-carrier project uses `PN_ship_hull_ice_carrier`, a VNR mega-carrier derivative with a third compatible aviation-deck mount. This preserves the inherited project reward in the VNR equipment system instead of leaving references to removed modules.
- Task 4: guarded initialization loads custom fleets once and does not require welcome-panel interaction. It supports a human-player selection and an all-AI fallback. The welcome panel is informational. Converted fleets are not loaded until after cleanup.
- Static checkpoint: 13 tests pass; the validator checks 1,696 files, 820 naval design blocks and 48 startup OOB paths (including alternate AI/air files), with no issues detected. Runtime verification is still in progress at this checkpoint.

## Naming

Imported additive files use `PN_`; exact base-game overrides retain their required relative paths. Each file, hash, destination and exception is recorded in `PN_vnr_import_manifest.json`. Original equipment/module/technology IDs remain compatibility identifiers. New integration logic follows Northwind naming.

## Validation

Run `python -m unittest discover -s tests -p test_PN_naval_validation.py` and `python tools/PN_validate_naval.py` from the project root. Runtime verification is recorded separately and must not be inferred from static checks.

The one-shot `PN_import_vnr.py`, `PN_convert_naval.py`, `PN_integrate_startup.py`, `PN_repair_naval_compatibility.py`, and `PN_convert_naval_rewards.py` tools record migration operations and refuse to reapply when their manifests already exist. They are not an updater: later compatibility repairs are recorded in the delivered files and manifest. Do not replace the embedded implementation by rerunning an importer against a newer Workshop copy.
