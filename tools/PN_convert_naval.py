"""One-shot, reference-aware Northwind naval migration. Review mappings in docs/naval."""
import copy
import json
from pathlib import Path
import re
import PN_validate_naval as n
from PN_import_vnr import render

CUSTOM = ('GRE', 'LAT', 'SOV', 'SWE', 'TUR', 'UKR')


def set_value(block, key, value):
    block[:] = [(k, v) for k, v in block if k != key] + [(key, value)]


def named_blocks(text, key):
    """Return exact source spans; unrelated script text/comments are never rendered."""
    tokens = [(m.group(), m.start(), m.end()) for m in n.TOKEN.finditer(text) if not m.group().isspace() and not m.group().startswith('#')]
    for i, (token, start, end) in enumerate(tokens):
        if token != key or i + 2 >= len(tokens) or tokens[i+1][0] != '=' or tokens[i+2][0] != '{':
            continue
        depth = 0
        for t, a, b in tokens[i+2:]:
            depth += (t == '{') - (t == '}')
            if depth == 0:
                yield start, b, n.first(n.parse(text[start:b]), key)
                break


def hull_for(old):
    if old == 'ship_hull_mega_carrier':
        return 'PN_ship_hull_ice_carrier'
    special = {'ship_hull_cruiser_panzerschiff': 'vnr_ship_hull_cruiser_2', 'ship_hull_cruiser_coastal_defense_ship': 'vnr_ship_hull_cruiser_coastal_defense_ship', 'ship_hull_pre_dreadnought': 'vnr_ship_hull_pre_dreadnought'}
    if old in special:
        return special[old]
    match = re.fullmatch(r'ship_hull_(light|cruiser|heavy|submarine|carrier)_([1-4])', old)
    if match:
        family, level = match.groups()
        # VNR adds a 1924 generation between the vanilla early and 1936 hulls.
        level = int(level)
        if family != 'carrier' and level > 1:
            level += 1
        return f'vnr_ship_hull_{family}_{level}'
    return 'vnr_' + old


def technology_unlocks(game, root):
    unlocks = {}
    for path in n.effective_files(game, root, 'common/technologies').values():
        for group in n.values(n.parse(n.read(path)), 'technologies'):
            for tech, spec in group:
                if not isinstance(spec, list):
                    continue
                for kind in ('enable_equipments', 'enable_equipment_modules'):
                    for item in n.bare(n.first(spec, kind, [])):
                        unlocks.setdefault(item, tech)
    return unlocks


def convert(design, hulls, modules):
    old = n.first(design, 'type')
    hull = hull_for(old)
    if hull not in hulls:
        raise ValueError(f'No hull mapping for {old}: {hull}')
    result = copy.deepcopy(design)
    set_value(result, 'type', hull)
    slots = n.slots_for(hulls, hull)
    defaults = dict(n.defaults_for(hulls, hull))
    choices = {k: v for k, v in defaults.items() if n.first(slots, k) is not None}
    original = n.first(design, 'modules', [])
    role = None
    if 'cruiser' in old and 'submarine' not in old:
        if 'panzerschiff' in old:
            role = 'ship_hull_cruiser_role_pz'
        elif 'coastal_defense' in old:
            role = 'ship_hull_cruiser_role_mo' if any(str(v).startswith('ship_heavy_battery_') for k,v in original) else 'ship_hull_cruiser_role_cd'
        elif any(str(v).startswith('ship_medium_battery') for k,v in original):
            role = 'ship_hull_cruiser_role_ca'
        else:
            role = 'ship_hull_cruiser_role_c'
        choices['fixed_ship_role_slot'] = role
    occupied = set()
    relocations = []
    for slot, module in original:
        if module == 'empty':
            # Original empty slots do not clear VNR's newly mandatory defaults.
            if n.first(slots, slot) is not None and n.first(n.first(slots, slot), 'required') != 'yes':
                choices[slot] = 'empty'
            continue
        replacement = module
        if module == 'ship_deck_space':
            replacement = 'ship_deck_space_open'
        if module == 'ship_escort_deck_space':
            replacement = 'ship_deck_space_small'
        if module == 'big_ship_deck_space':
            replacement = 'ship_deck_space_mega'
        if module.startswith('ship_armor_ice_carrier_deck'):
            replacement = 'carrier_armor_deck'
        if old == 'ship_hull_mega_carrier' and module.startswith('ship_armor_cruiser_'):
            replacement = 'ship_armor_carrier_heavy_3'
        if old == 'ship_hull_super_heavy_1' and module.startswith('heavy_ship_engine_'):
            replacement = 'super_heavy_ship_engine_1'
        if 'cruiser' in old and module.startswith('light_ship_engine_'):
            replacement = 'cruiser_ship_engine_' + module.rsplit('_',1)[1]
        if module == 'ship_armor_carrier_deck':
            replacement = 'carrier_armor_deck'
        if module == 'ship_light_battery_sub':
            replacement = 'sub_deck_gun_1'
        if 'submarine' in old and module.startswith('ship_airplane_launcher_'):
            replacement = 'sub_airplane_launcher_1'
        if 'panzerschiff' in old and module.startswith('ship_heavy_battery_'):
            replacement = 'ship_medium_heavy_battery_1'
        if 'carrier_conversion' in old and module.startswith('carrier_ship_engine'):
            replacement = 'heavy_ship_engine_' + module.rsplit('_',1)[1] if old.endswith('_bb') else module
        if (('heavy' in old or 'carrier' in old) and module.startswith('dp_ship_secondaries_')):
            replacement = module + '_bb'
        if ('cruiser' in old and 'submarine' not in old and module.startswith('ship_secondaries_')):
            replacement = module + '_light'
        if replacement not in modules:
            raise ValueError(f'No module mapping for {module} in {n.first(design,"name")}')
        category = n.first(modules[replacement], 'category')
        allowed = [k for k, spec in slots if category in n.bare(n.first(spec, 'allowed_module_categories', []))]
        preferred = slot
        if module == 'ship_armor_carrier_deck':
            preferred = 'fixed_ship_flight_deck_slot'
        if 'submarine' in old and module == 'ship_light_battery_sub':
            preferred = 'fixed_ship_battery_slot' if 'cruiser_submarine' in old else 'fixed_ship_secondaries_slot'
        if preferred not in allowed or preferred in occupied:
            available = [k for k in allowed if k not in occupied and choices.get(k, 'empty') == 'empty']
            if not available:
                available = [k for k in allowed if k not in occupied]
            if not available:
                raise ValueError(f'No compatible free slot for {replacement} in {n.first(design,"name")} ({hull})')
            preferred = available[0]
        choices[preferred] = replacement
        occupied.add(preferred)
        if slot != preferred or module != replacement:
            relocations.append(dict(from_slot=slot, from_module=module, slot=preferred, module=replacement))
    # Include all required defaults explicitly, so saved designs are unambiguous.
    set_value(result, 'modules', list(choices.items()))
    errors = n.check_design(result, hulls, modules)
    if errors:
        raise ValueError((n.first(design,'name'), errors))
    return result, dict(original_hull=old, hull=hull, role=role, relocations=relocations, modules=choices, rationale='Preserve original weapons/engine/armor where compatible; select VNR era hull and role, relocate modules only to permitted slots, add mandatory hull defaults.')


def main():
    mapping_path = n.ROOT / 'docs/naval/PN_naval_conversion.json'
    if mapping_path.exists():
        raise SystemExit('Conversion already recorded; do not reapply')
    hulls, modules = n.equipment_database(n.GAME, n.ROOT)
    unlocks = technology_unlocks(n.GAME, n.ROOT)
    effects, entries, lookup, writes = [], [], {}, []
    # Country histories retain their exact conditional/date placement via effect calls.
    for path in (n.ROOT / 'history/countries').glob('*.txt'):
        text = n.read(path)
        edits = []
        tag = path.name[:3]
        count = 0
        for start, end, design in named_blocks(text, 'create_equipment_variant'):
            if not str(n.first(design, 'type', '')).startswith('ship_hull_'):
                continue
            converted, info = convert(design, hulls, modules)
            count += 1
            effect = f'PN_{tag}_naval_design_{count}'
            equipment = [info['hull']] + [v for v in info['modules'].values() if v != 'empty']
            techs = sorted({unlocks[e] for e in equipment if e in unlocks})
            body = [('set_technology', [(t, '1') for t in techs] + [('popup','no')]), ('create_equipment_variant', converted)]
            effects.append((effect, body))
            edits.append((start, end, effect + ' = yes'))
            entries.append(dict(country=tag, name=n.first(design, 'name'), source=path.relative_to(n.ROOT).as_posix(), effect=effect, required_techs=techs, **info))
            lookup[(tag, n.first(design, 'name'))] = info['hull']
        for start,end,replacement in reversed(edits):
            text = text[:start]+replacement+text[end:]
        if edits:
            writes.append((path, text))
    writes.append((n.ROOT/'common/scripted_effects/PN_naval_starting_variants.txt', '# Northwind original designs converted to VNR; history calls preserve original date/DLC gates.\n' + render(effects) + '\n'))
    baseline = json.loads((n.ROOT/'docs/naval/PN_naval_baseline.json').read_text(encoding='utf-8'))
    shipmap = []
    for tag in CUSTOM:
        original_path = n.ROOT/f'history/units/{tag}_1936_naval_mtg.txt'
        text = n.read(original_path)
        # Equipment keys are replaced by the referenced owner and exact class, not hull alone.
        for a,b,ship in reversed(list(named_blocks(text,'ship'))):
            equipment = n.first(ship,'equipment',[])
            converted = copy.deepcopy(ship)
            neweq = []
            for oldh, spec in equipment:
                key = n.first(spec,'owner'),n.first(spec,'version_name')
                newh = lookup.get(key)
                if newh is None:
                    raise ValueError(f'Unresolved custom ship: {key}')
                neweq.append((newh,spec))
            set_value(converted,'equipment',neweq)
            text=text[:a]+render([('ship',converted)])+text[b:]
        target=n.ROOT/f'history/units/PN_{tag}_1936_naval.txt'
        writes.append((target,text))
        writes.append((original_path,'# Northwind navy is loaded once by PN_initialize_navy after VNR technology setup.\n'))
        shipmap.extend(n.ship_records(n.parse(text),target.relative_to(n.ROOT).as_posix()))
    writes.append((mapping_path,json.dumps(dict(designs=entries,ships=shipmap),indent=2,ensure_ascii=False)))
    for path, content in writes:
        path.write_text(content,encoding='utf-8')
    print(f'Converted {len(entries)} country-history designs and {len(shipmap)} Northwind ships')


if __name__=='__main__':
    main()
