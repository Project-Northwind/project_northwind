# VNR integration into Project Northwind

## Outcome and scope

Embed the locally installed Vanilla Navy Rework (Workshop 2993766165, descriptor version v3.3 - Das Boot) directly into Northwind. Northwind must run without separately enabling VNR. Preserve Northwind's political history, land and air forces, and custom naval identity while converting its ships to VNR equipment. Target the installed HOI4 1.19 series, with Northwind currently declaring 1.19.3.0.

The user approved this integration approach on 2026-10-20. The supplied MrPunk notes are explanatory references, not requirements; the installed source determines actual behavior.

## Source and import boundaries

Source: `C:/Program Files (x86)/Steam/steamapps/workshop/content/394360/2993766165`.

Import VNR naval equipment, modules, technology, AI, decisions, events, graphics, interface and localisation with an explicit collision inventory. Preserve the Northwind descriptor identity and existing credits. Merge any necessary replace_path declarations individually. Do not inherit the VNR descriptor's Road to 56 and Last Stand dependencies automatically: inspect their references and adapt or remove integration-specific behavior that Northwind cannot satisfy.

Keep unrelated Northwind systems intact. Record source version and intentional deviations so later Workshop updates cannot silently replace the embedded implementation.

## Fleet and design conversion

Northwind owns custom naval OOBs for GRE, LAT, SOV, SWE, TUR and UKR. Preserve every ship's name, country owner, class name, fleet and task-force membership, port/location, and pride designation. Preserve ship counts and existing production progress where specified. Audit other country histories and embedded naval sections in mixed OOBs as well; the six filenames are an initial inventory, not a scope limit.

Convert each used hull to a VNR hull appropriate to its era and role. Convert modules using slot and category compatibility, including mandatory VNR role/engine/armor requirements. A global string substitution is insufficient for cruisers and other hulls with multiple roles. Reuse matching VNR historical designs only when they preserve the intended Northwind class; otherwise define a converted Northwind design. Capture class-to-hull/module mappings and any substantive interpretation for review.

Update corresponding technology grants, production queues, scripted designs, equipment rewards and ship-spawning references. Audit inherited base-game content where VNR disables vanilla equipment, so reachable rewards do not silently grant unusable ships.

## Startup loading

VNR's `navy_rework.0` currently calls `delete_starting_naval_oob`, grants technology and variants, and loads historical OOBs. Copying it unchanged would erase Northwind fleets. Adapt it so technologies and required designs exist before converted fleets load, and each country's starting navy loads exactly once. Northwind custom fleets take precedence over VNR historical replacements. Other supported countries retain VNR startup coverage unless Northwind history explicitly requires another composition.

Initialization must work for human and AI countries and must not depend solely on a human dismissing a splash. Guard repeated initialization to prevent duplicate fleets, designs or bonuses after reloads or repeated startup effects. Preserve carrier aircraft associations without duplicating or removing Northwind air formations. Do not destroy already converted Northwind ships through a broad cleanup effect.

## Compatibility and supported starts

Audit DLC conditions, custom tags, missing countries, treaty membership, doctrine effects and any Road to 56/Last Stand assumptions in the installed VNR source. Guard or adapt unsupported integrations without importing unrelated systems.

VNR advertises 1936 support. Inspect the starts Northwind actually exposes. Every exposed start must either receive an explicit supported conversion or be clearly identified as unsupported before completion; do not silently claim 1939 compatibility from dated history blocks alone. Existing saves are not a migration target; validate fresh games.

## Verification and acceptance

Establish a baseline before modifications, including available game logs and source inventories. Add a repeatable validator for the migration's meaningful invariants: balanced script structure, resolvable hull/module/technology and OOB references, compatible module slots, matching OOB class names and owners, preserved Northwind ship inventory, and absence of duplicate startup loading. Distinguish intentional legacy definitions from active vanilla references.

Check imported graphics paths and localisation keys, descriptor conflicts, and unresolved external-mod references. Compare detected issues against the baseline and report inherited VNR problems separately from newly introduced problems; fix inherited problems that prevent the integration functioning.

Run an actual fresh game with Northwind enabled where the local runtime permits. Inspect new error logs, verify custom fleets and the designer, advance time to exercise startup/AI behavior, and check save/reload initialization. Static validation is necessary but cannot establish runtime correctness. If runtime validation is unavailable, report the exact unverified checks and do not claim an error-free or perfect port.

## Deliverables

Embedded VNR assets and scripts; converted Northwind designs, fleets and reachable naval grants; deterministic startup integration; a source/deviation record; repeatable validation with results; and a concise account of any remaining runtime limitations. Keep changes reviewable in the existing repository and preserve unrelated work.
