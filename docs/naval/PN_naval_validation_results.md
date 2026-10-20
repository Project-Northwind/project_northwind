# Northwind VNR validation — 20 October 2026

Implemented in the installed Northwind directory on branch `VNR-Fix`. VNR v3.3 “Das Boot” is embedded; enable Northwind alone and begin a new 1936 campaign. Pre-integration saves and the inherited 1939 bookmark are outside the supported migration.

## Automated checks

- `python -m unittest discover -s tests -p test_PN_naval_validation.py`: 16 tests passed.
- `python tools/PN_validate_naval.py --output docs/naval/PN_naval_static_results.json`: no issues across 1,890 script files, 1,276 naval design blocks and 48 startup OOB paths, including alternate AI/air OOBs.
- The immutable inventory comparison preserves all 139 Northwind ships, including owners, ship names, classes, fleets, task forces, ports and pride flags, and all 12 original shipyard orders with progress and factory allocations.
- Designer layout checks cover every declared module slot in the delivered ship layouts and the engine-required module-picker stat icons. Carrier-unit checks retain valid AI deployment settings.
- `git diff --check`: passed after whitespace normalization.
- Independent final static review found two startup/multiplayer issues; both were fixed. The reviewer reported no remaining static blockers.

## Engine checks

Tested with installed HOI4 1.19.3.0, Northwind as the only enabled mod, and the installed DLC configuration. The game was cold-restarted after equipment and GUI repairs.

| Check | Observed result |
| --- | --- |
| Fresh 1936 initialization | Reached Ukraine campaign without naval database/load errors |
| Repeated initialization | Debug effect called initializer twice again; all six fleet checks passed: GRE 20, LAT 7, SOV 81, SWE 12, TUR 9, UKR 10 |
| Custom fleet UI | Ukraine's 8 surface ships and 2 submarines loaded, with original names and flagship |
| Designer/module picker | Converted Bohdan Khmelnytsky Class displayed VNR modules; armor choices opened successfully; cold reload confirmed missing-layout/stat-icon errors eliminated |
| Production | Converted cruiser class appeared in build list and a test production order was created successfully |
| Technology UI | VNR hull/armor tree and cruiser unlock details displayed; engine enforced its propulsion prerequisite |
| Time advance | Fresh campaign advanced to 18 January; saved locally |
| Save/reload | Cold-reloaded `UKR_1936_01_18_06.hoi4`; fleet retained 10 ships; advanced to 31 January |
| AI aircraft regression | Before repair, repeated invalid `deploy_air_wing_command` errors; after restoring current engine carrier categories and wing settings, none occurred from 18–31 January |

Evidence summaries and exact final log messages are in `PN_naval_runtime_results.json`. Original and intermediate logs remain locally under the ignored `.superpowers/sdd/2026-10-20-vnr-integration` folder.

## Existing errors retained

The final run reported only the existing DLC checksum/other Workshop descriptor warnings, the existing Hungarian decision-category reference, the existing `government` localization collision, and the unchanged Northwind `PN_expanded_government.txt` reference to undefined `nationalization_capital`. The first three groups are present in the saved pre-import logs; the government script is unchanged from baseline commit `4f332c4`. These are unrelated to the naval integration and have not been hidden or removed.

## Limits of the evidence

This is a successful static validation and single-player startup/designer/production/save-reload smoke test, not proof of every future campaign state. Multiplayer OOS behavior, alternate DLC configurations, every delayed focus/event/project reward, every special hull/refit path, actual carrier-wing composition in each major fleet, and long AI campaigns were not exhaustively exercised. Reward designs and carrier OOB references were checked statically. No claim of a completely error-free base mod is made.
