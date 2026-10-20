# Northwind VNR Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Native execution was selected and approved.

**Goal:** Embed VNR into Northwind and convert Northwind's existing ships without losing their identities or introducing integration errors.

**Architecture:** Import a recorded snapshot using Northwind naming and required-path override exceptions. Convert Northwind designs and OOBs together, then replace VNR's destructive historical startup with guarded initialization that respects custom fleets.

**Tech Stack:** HOI4 Clausewitz scripts, Lua defines, GUI/GFX definitions, YAML localisation, Python standard-library validation, installed HOI4 runtime.

**Spec:** `docs/superpowers/specs/2026-10-20-vnr-integration-design.md`

## Global Constraints

- Northwind must run without separately enabling VNR.
- Target the installed HOI4 1.19 series, with Northwind currently declaring 1.19.3.0.
- Use `PN_` prefixes for new and imported integration-owned filenames.
- Exact-name base-game overrides and suppression files are exceptions to the `PN_` filename rule when HOI4 requires the original path to replace a vanilla file.
- Preserve every ship's name, country owner, class name, fleet and task-force membership, port/location, and pride designation.
- Existing saves are not a migration target; validate fresh games.
- Keep unrelated Northwind systems intact.
- Do not claim an error-free or perfect port without runtime evidence.

## Review Focus

- Reloading or dismissing the welcome panel twice must not recreate fleets or bonuses (Task 4).
- Cruiser roles, mandatory modules and cross-country designs must resolve correctly (Task 3).
- Renamed override files must not restore vanilla definitions or break asset paths (Task 2).
- Human/AI startup and absent or custom tags must work without external mod dependencies (Tasks 4–5).
- Carrier air wings and delayed naval rewards must survive conversion without duplication (Tasks 3–5).

## Task 1: Record the baseline and define the validation inputs

**Files:** Create `tools/PN_validate_naval.py`, `tests/test_PN_naval_validation.py`, `docs/naval/PN_naval_baseline.json`, and `docs/naval/PN_vnr_integration.md`.

**Interfaces:** Baseline stores source version/hash inventory, original Northwind naval designs and ship records, startup entry points, exposed bookmarks, DLC branches, existing source conflicts and log timestamps. Validator CLI: `python tools/PN_validate_naval.py --game-root <path>`; output groups newly introduced failures, inherited failures and unresolved runtime checks, with nonzero exit for integration failures.

- [x] Inventory the installed source and game, Northwind histories, mixed OOBs, focus/event/scripted naval grants, current logs and available runtime controls before mutation. Identify all active starts and preserve unrelated changes.
- [x] Write validator tests for braces inside comments/quoted strings, repeated block keys, unresolved hull/module references and an OOB referencing a missing owner/class combination. Run `python -m unittest discover -s tests -p test_PN_naval_validation.py`; confirm failure before implementation.
- [x] Implement the parser and inventory checks with repeated keys retained; do not validate Clausewitz through a flat dictionary or regex-only nested-block substitutions.
- [x] Generate and inspect the baseline. Record original Northwind ship records independently of files later rewritten; confirm GRE/LAT/SOV/SWE/TUR/UKR coverage plus any embedded naval units discovered.
- [x] Run the validator unit tests and commit only Task 1 files.

## Task 2: Import VNR with Northwind naming and explicit overrides

**Files:** Create `docs/naval/PN_vnr_import_manifest.json`; import into existing `common`, `events`, `history/units`, `gfx`, `interface`, and `localisation` directories; modify `descriptor.mod` and provenance documentation. Preserve existing credits.

**Interfaces:** Manifest records each source path/hash, destination path, exact-path exception reason, collision resolution and retained identifier rationale. Existing VNR equipment/module/tech IDs remain where needed; new integration code uses Northwind conventions.

- [x] Add failing checks for manifest coverage, duplicate effective definitions, dangling renamed asset/OOB paths, missing localisation language headers and unjustified non-`PN_` filenames.
- [x] Build the collision map against Northwind and base-game paths. Separate original-path suppression/override files from additive definitions before assigning destination names. Resolve lexical load-order dependencies explicitly.
- [x] Import required VNR systems and assets using the manifest. Rewrite filename/path references consistently, retain encoding requirements, and preserve Northwind content on collisions.
- [x] Merge only necessary naval `replace_path` declarations; do not copy Workshop identity or Road to 56/Last Stand dependencies into Northwind's descriptor.
- [x] Run naming, path, duplicate-definition, syntax and localisation checks; record inherited source issues and fix blockers. Commit the coherent import checkpoint, explicitly marking startup conversion incomplete.

## Task 3: Convert Northwind ships and all active naval grants

**Files:** Create `common/scripted_effects/PN_naval_starting_variants.txt`, `common/scripted_effects/PN_naval_starting_techs.txt`, `docs/naval/PN_naval_conversion.json`; modify relevant `history/countries` entries and the six existing custom naval OOBs or their manifest-recorded `PN_` replacements. Audit `common/national_focus/soviet.txt`, `events/Germany.txt`, mixed OOBs and inherited reachable naval rewards.

**Interfaces:** Conversion map keys are country plus original variant name; values specify VNR hull, modules, role, tech requirements and justification. Converted fleets reference those exact names and owners. Historical VNR fleets remain available for countries without Northwind custom replacements.

- [x] Add failing assertions comparing converted ship identities/counts/task forces/ports/pride and production progress against the immutable baseline. Add invalid cruiser-role, missing mandatory-slot and foreign-owner class fixtures.
- [x] Convert designs individually by role/era and permitted slots, using source hull/module definitions. Preserve class names; document approximations rather than substituting unrelated historical fleets.
- [x] Update all active OOB hull keys and production/design references together. Grant required VNR technology before the corresponding converted design/fleet loads; prevent still-active vanilla starting variants from becoming the sole reference target.
- [x] Convert reachable ship-design rewards and naval grants, including inherited base-game files where necessary. Preserve unrelated effects within overridden files. Inventory any unavoidable exact-path overrides in the manifest.
- [x] Validate hull/module compatibility, tech availability, OOB owner/class resolution, preserved fleet inventory and active legacy references. Commit the converted naval content.

## Task 4: Make startup deterministic and adapt external assumptions

**Files:** Create `common/on_actions/PN_naval_startup.txt`, `common/scripted_effects/PN_naval_initialization.txt`; modify imported `events/PN_naval_rework.txt`, welcome GUI and related imported effects/triggers using the manifest's actual destinations.

**Interfaces:** `PN_initialize_navy` is the sole initialization dispatcher. A global `PN_naval_initialized` flag guards the complete sequence. Custom-country paths grant technologies/designs and load converted Northwind OOBs once; other country paths use VNR historical data. Welcome-panel actions cannot bypass the guard.

- [x] Add failing checks for two calls reaching unguarded fleet loads, duplicate history/startup fleet loading, initialization requiring a human panel click, and broad deletion of converted ships.
- [x] Route startup and welcome actions through the guarded dispatcher. Establish ordering: prerequisite techs, designs, fleets, carrier-air associations, then completion flag. Remove or narrow broad cleanup; suppress original OOB paths that would otherwise double-load ships.
- [x] Inspect all imported Road to 56/Last Stand rules, missing tags, treaty assumptions and doctrine/special-project references against Northwind and the installed game. Guard or remove unsupported branches with documented reasons; preserve valid VNR functions.
- [x] Validate no duplicate initialization routes, every custom fleet has exactly one load path and carrier air formations remain consistent. Cover both human and AI entry points and all exposed supported starts.
- [x] Commit startup integration and documented compatibility decisions.

## Task 5: Verify the integrated mod in the game

**Files:** Update `docs/naval/PN_vnr_integration.md`, create `docs/naval/PN_naval_validation_results.md`, and update plan checkboxes from actual evidence.

**Interfaces:** Results record exact source/game versions, commands, dates, baseline comparison, runtime scenarios, failures fixed and checks not performed. No static pass is represented as runtime proof.

- [x] Run unit tests, the full validator, and `git diff --check`. Resolve integration failures; investigate inherited failures affecting active naval behavior.
- [x] Launch a fresh Northwind-only game where permitted, retaining any existing user session. Collect newly generated logs separately from the baseline.
- [ ] Inspect all six custom fleets and representative major-country fleets, ship designer/module selections, technology research, production and at least one reachable naval reward. Verify carrier wings and AI initialization; advance time for AI production/events.
- [ ] Save/reload and repeat the welcome/init trigger to test duplicate prevention. Check every exposed supported start and available DLC branches; explicitly report branches unavailable to this installation.
- [x] Fix relevant runtime errors, rerun affected checks, and complete a whole-change review of inventory preservation, effective override paths, startup ordering and missing references.
- [x] Record final results and remaining limitations; commit the verified integration without claiming checks that were not run.

## Execution choice

Recommend native execution in this session: the import manifest, variant conversion and startup ordering share substantial state, so one implementer can keep the migration consistent. User may instead select subagent-driven execution with independent task reviews. One independent final static reviewer was used as required by the execution workflow; implementation remained native.

## Plan self-review

Spec requirements map to Tasks 1–5. Naming exceptions, repeated initialization, missing/custom tags, foreign-owner designs, carrier wings and delayed grants have explicit checks. Baseline and manifest are created before migration and consumed by later validation. Runtime-unavailable outcomes remain explicit limitations rather than completion claims.

## Runtime coverage disposition

The two unchecked Task 5 scenario matrices were partially exercised: six fleet-count assertions, Ukraine fleet/designer/module picker, build list and production order, naval research UI, AI time advance, and cold save/reload. Exhaustive delayed rewards, major carrier-wing counts, alternate DLC configurations and multiplayer remain unverified; see `docs/naval/PN_naval_validation_results.md`.
