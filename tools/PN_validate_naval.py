"""Northwind naval script inspection. Blocks retain order and repeated keys."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GAME = Path('C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV')
SOURCE = Path('C:/Program Files (x86)/Steam/steamapps/workshop/content/394360/2993766165')
TOKEN = re.compile(r'\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|[{}]|[<>!?]?=|[<>!]|[^\s{}=<>!"#]+')


class Key(str):
    def __new__(cls, value, operator='='):
        key = super().__new__(cls, value)
        key.operator = operator
        return key


def read(path):
    return Path(path).read_text(encoding='utf-8-sig', errors='replace')


def parse(text):
    tokens = [m.group() for m in TOKEN.finditer(text) if not m.group().isspace() and not m.group().startswith('#')]
    pos = 0

    def block(nested=False):
        nonlocal pos
        result = []
        while pos < len(tokens):
            token = tokens[pos]
            if token == '}':
                if not nested:
                    raise ValueError('Unexpected closing brace')
                pos += 1
                return result
            pos += 1
            if token == '{':
                result.append((None, block(True)))
            elif pos < len(tokens) and tokens[pos] in ('=', '<', '>', '<=', '>=', '!=', '?='):
                operator = tokens[pos]
                pos += 1
                if pos >= len(tokens):
                    raise ValueError('Missing assignment value')
                value = tokens[pos]
                pos += 1
                result.append((Key(unquote(token), operator), block(True) if value == '{' else unquote(value)))
            else:
                result.append((None, unquote(token)))
        if nested:
            raise ValueError('Unclosed block')
        return result

    return block()


def unquote(value):
    return value[1:-1] if value.startswith('"') and value.endswith('"') else value


def values(block, key):
    return [v for k, v in block if k == key] if isinstance(block, list) else []


def first(block, key, default=None):
    return next(iter(values(block, key)), default)


def walk(block, key):
    for k, v in block:
        if k == key:
            yield v
        if isinstance(v, list):
            yield from walk(v, key)


def bare(block):
    return [v for k, v in block if k is None and isinstance(v, str)] if isinstance(block, list) else []


def effective_files(game, mod, directory, suffix='.txt'):
    result = {}
    for root in (game, mod):
        base = root / directory
        if base.exists():
            for path in base.rglob('*' + suffix):
                result[path.relative_to(base).as_posix()] = path
    return result


def equipment_database(game, mod):
    hulls, modules = {}, {}
    for path in effective_files(game, mod, 'common/units/equipment').values():
        tree = parse(read(path))
        for group in values(tree, 'equipments'):
            for key, value in group:
                if isinstance(value, list):
                    hulls[key] = value
        for group in values(tree, 'equipment_modules'):
            for key, value in group:
                if isinstance(value, list):
                    modules[key] = value
    return hulls, modules


def inherited(hulls, hull, key, seen=None):
    seen = set() if seen is None else seen
    if hull in seen or hull not in hulls:
        return None
    seen.add(hull)
    own = first(hulls[hull], key)
    if own is not None and own != 'inherit':
        return own
    parent = first(hulls[hull], 'parent') or first(hulls[hull], 'archetype')
    return inherited(hulls, parent, key, seen)


def slots_for(hulls, hull):
    slots = inherited(hulls, hull, 'module_slots') or []
    result = []
    for slot, spec in slots:
        seen = set()
        while isinstance(spec, str):
            if spec == 'inherit':
                parent = first(hulls[hull], 'parent') or first(hulls[hull], 'archetype')
                spec = first(slots_for(hulls, parent), slot, []) if parent in hulls else []
                continue
            if spec in seen:
                raise ValueError(f'Cyclic slot alias: {hull}/{slot}')
            seen.add(spec)
            spec = first(slots, spec, [])
        result.append((slot, spec))
    return result


def defaults_for(hulls, hull, seen=None):
    seen = set() if seen is None else seen
    if hull not in hulls or hull in seen:
        return []
    seen.add(hull)
    parent = first(hulls[hull], 'parent') or first(hulls[hull], 'archetype')
    result = dict(defaults_for(hulls, parent, seen))
    own = first(hulls[hull], 'default_modules', [])
    if isinstance(own, list):
        result.update(own)
    return list(result.items())


def check_design(design, hulls, modules):
    hull = first(design, 'type')
    if hull not in hulls:
        return [f'Unknown hull {hull}']
    slots = slots_for(hulls, hull)
    choices = [(k, v) for k, v in defaults_for(hulls, hull) if first(slots, k) is not None]
    explicit = first(design, 'modules', [])
    choices = [(k, v) for k, v in choices if first(explicit, k) is None] + explicit
    problems = []
    for slot, spec in slots:
        choice = first(choices, slot)
        if first(spec, 'required') == 'yes' and choice in (None, 'empty'):
            problems.append(f'{hull}: required slot {slot} missing')
    for slot, module in choices:
        if module == 'empty':
            continue
        if module not in modules:
            problems.append(f'{hull}: unknown module {module}')
            continue
        spec = first(slots, slot)
        if spec is None:
            problems.append(f'{hull}: unknown slot {slot}')
        elif first(modules[module], 'category') not in bare(first(spec, 'allowed_module_categories', [])):
            problems.append(f'{hull}: {module} incompatible with {slot}')
    used_categories = {first(modules[v], 'category') for k,v in choices if v in modules}
    for slot, module in choices:
        if module in modules:
            banned = set(bare(first(modules[module], 'forbid_module_categories', [])))
            for category in banned & used_categories:
                problems.append(f'{hull}: {module} forbids {category}')
    return problems


def check_ship(ship, designs):
    problems = []
    for hull, equipment in first(ship, 'equipment', []):
        owner, name = first(equipment, 'owner'), first(equipment, 'version_name')
        available = designs.get((owner, name))
        if available != hull and not (isinstance(available, (set, list, tuple)) and hull in available):
            problems.append(f'{first(ship, "name")}: unresolved {owner}/{name}/{hull}')
    return problems


def ship_records(tree, file):
    result = []
    for units in values(tree, 'units'):
        for fleet in values(units, 'fleet'):
            for task in values(fleet, 'task_force'):
                for ship in values(task, 'ship'):
                    result.append(dict(file=file, fleet=first(fleet, 'name'), base=first(fleet, 'naval_base'), task=first(task, 'name'), location=first(task, 'location'), ship=ship))
        for ship in values(units, 'navy'):
            result.append(dict(file=file, ship=ship))
    return result


def snapshot():
    records, variants, syntax = [], {}, []
    for path in (ROOT / 'history/units').glob('*.txt'):
        tree = parse(read(path))
        records.extend(ship_records(tree, path.relative_to(ROOT).as_posix()))
    for path in (ROOT / 'history/countries').glob('*.txt'):
        designs = [v for v in walk(parse(read(path)), 'create_equipment_variant') if str(first(v, 'type', '')).startswith(('ship_', 'vnr_'))]
        if designs:
            variants[path.name] = designs
    for path in SOURCE.rglob('*'):
        if path.suffix in ('.txt', '.gui', '.gfx'):
            try:
                parse(read(path))
            except ValueError as error:
                syntax.append([path.relative_to(SOURCE).as_posix(), str(error)])
    logs = ROOT.parent.parent / 'logs'
    log_info = {p.name: dict(size=p.stat().st_size, mtime=p.stat().st_mtime) for p in logs.glob('*.log')}
    result = dict(source_descriptor=read(SOURCE / 'descriptor.mod'), source_files={p.relative_to(SOURCE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCE.rglob('*') if p.is_file()}, ships=records, variants=variants, source_syntax_issues=syntax, logs=log_info)
    target = ROOT / 'docs/naval/PN_naval_baseline.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Refusing to overwrite immutable naval baseline')
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Baseline: {len(records)} ships, {sum(map(len, variants.values()))} naval variant blocks, {len(result["source_files"])} source files, {len(syntax)} inherited syntax issues')


def identity(record):
    ship = record['ship']
    equipment = [(first(v, 'owner'), first(v, 'version_name'), first(v, 'amount')) for k, v in first(ship, 'equipment', [])]
    # Keep all ship properties other than the intentionally changed hull identifier.
    properties = sorted((k, v) for k, v in ship if k != 'equipment')
    return json.dumps([record.get('fleet'), record.get('base'), record.get('task'), record.get('location'), properties, equipment], sort_keys=True)


def validate_custom_fleets():
    from collections import Counter
    baseline = json.loads(read(ROOT / 'docs/naval/PN_naval_baseline.json'))
    problems = []
    current = []
    for tag in ('GRE','LAT','SOV','SWE','TUR','UKR'):
        path = ROOT / f'history/units/PN_{tag}_1936_naval.txt'
        if not path.exists():
            problems.append(f'Missing converted fleet: {tag}')
        else:
            current.extend(ship_records(parse(read(path)), path.relative_to(ROOT).as_posix()))
    if Counter(map(identity, baseline['ships'])) != Counter(map(identity, current)):
        problems.append('Northwind fleet identity/count/task-force/port/pride/progress differs from baseline')
    designs = {}
    variants = ROOT / 'common/scripted_effects/PN_naval_starting_variants.txt'
    if variants.exists():
        for effect, body in parse(read(variants)):
            for design in walk(body, 'create_equipment_variant'):
                designs[(effect.split('_')[1], first(design, 'name'))] = first(design, 'type')
    hulls, modules = equipment_database(GAME, ROOT)
    for record in current:
        problems.extend(check_ship(record['ship'], designs))
    if variants.exists():
        for variant in walk(parse(read(variants)), 'create_equipment_variant'):
            problems.extend(f'{first(variant,"name")}: {p}' for p in check_design(variant,hulls,modules))
    return problems


def validate_integration(game=GAME):
    from collections import defaultdict
    problems = validate_custom_fleets() + validate_custom_production()
    manifest = json.loads(read(ROOT/'docs/naval/PN_vnr_import_manifest.json'))
    rewards = json.loads(read(ROOT/'docs/naval/PN_naval_rewards.json'))
    paths = {e['destination'] for e in manifest['files']} | set(rewards['files'])
    paths |= {p.relative_to(ROOT).as_posix() for p in (ROOT/'common/scripted_effects').glob('PN_*.txt')}
    paths |= {'common/on_actions/PN_naval_startup.txt','common/technologies/PN_naval_compatibility.txt','common/units/names_ships/PN_naval_compatibility_names.txt'}
    paths |= {p.relative_to(ROOT).as_posix() for directory in ('history/units','history/countries','common/special_projects/projects') for p in (ROOT/directory).glob('*.txt')}
    paths |= {'common/script_enums.txt','common/units/air.txt'}
    for entry in manifest['files']:
        path=ROOT/entry['destination']
        if not path.exists():problems.append('Missing imported file: '+entry['destination'])
        if not path.name.startswith('PN_') and not entry.get('exception'):problems.append('Undocumented naming exception: '+entry['destination'])
        if entry.get('suppression_path') and not (ROOT/entry['suppression_path']).exists():problems.append('Missing vanilla suppression: '+entry['suppression_path'])
    hulls,modules=equipment_database(game,ROOT)
    techs=set()
    for p in effective_files(game,ROOT,'common/technologies').values():
        for group in values(parse(read(p)),'technologies'):techs.update(k for k,v in group if isinstance(v,list))
    namegroups=set()
    for p in effective_files(game,ROOT,'common/units/names_ships').values():
        namegroups.update(k for k,v in parse(read(p)) if isinstance(v,list))
    designs=defaultdict(set)
    design_count=0
    # Build country/class/hull triples, retaining different eras with the same class name.
    for p in (ROOT/'common/scripted_effects').glob('*.txt'):
        try:tree=parse(read(p))
        except ValueError:continue
        for effect,body in tree:
            match=re.match(r'(?:PN_)?([A-Z]{3})_',str(effect))
            if match and isinstance(body,list):
                for d in walk(body,'create_equipment_variant'):
                    designs[(match[1],first(d,'name'))].add(first(d,'type'))
    for rel in sorted(paths):
        p=ROOT/rel
        if not p.exists() or p.suffix not in ('.txt','.gui','.gfx','.asset'):continue
        text=read(p)
        try:tree=parse(text)
        except ValueError as error:
            problems.append(f'{rel}: {error}');continue
        for asset in re.findall(r'"(gfx/[^"\n]+)"',text):
            if not (ROOT/asset).exists() and not (game/asset).exists():problems.append(f'{rel}: missing asset {asset}')
        for d in walk(tree,'create_equipment_variant'):
            hull=str(first(d,'type',''))
            if hull.startswith(('vnr_ship_','PN_ship_')):
                design_count+=1
                problems.extend(f'{rel}/{first(d,"name")}: {issue}' for issue in check_design(d,hulls,modules))
                group=first(d,'name_group')
                if group and group not in namegroups:problems.append(f'{rel}: missing name group {group}')
        for grants in walk(tree,'set_technology'):
            for tech,value in grants:
                if tech!='popup' and tech not in techs:problems.append(f'{rel}: missing technology grant {tech}')
    initialization=parse(read(ROOT/'common/scripted_effects/PN_naval_initialization.txt'))
    loads=set(walk(initialization,'load_oob'))
    ship_count=0
    for stem in loads:
        p=ROOT/'history/units'/f'{stem}.txt'
        if not p.exists():
            problems.append('Missing startup OOB: '+stem);continue
        for ship in walk(parse(read(p)),'ship'):
            ship_count+=1;problems.extend(check_ship(ship,designs))
    # Loading a custom fleet in country history as well as startup would double it.
    for p in (ROOT/'history/countries').glob('*.txt'):
        for value in walk(parse(read(p)),'set_naval_oob'):
            if str(value).startswith('PN_'):problems.append(f'{p.name}: custom fleet loads before guarded initialization')
    return dict(checked_files=len(paths), naval_design_blocks=design_count, startup_oobs=len(loads), startup_ship_records_including_alternate_ai_oobs=ship_count, preserved_northwind_ships=139, issues=sorted(set(problems)))


def validate_custom_production():
    from collections import Counter
    original=json.loads(read(ROOT/'docs/naval/PN_naval_production_baseline.json'))
    current=[]
    problems=[]
    conversion=json.loads(read(ROOT/'docs/naval/PN_naval_conversion.json'))
    designs={(d['country'],d['name']):d['hull'] for d in conversion['designs']}
    for tag in ('GRE','LAT','SOV','SWE','TUR','UKR'):
        tree=parse(read(ROOT/f'history/units/PN_{tag}_1936_naval.txt'))
        for order in walk(tree,'add_equipment_production'):
            current.append(dict(country=tag,order=order))
            equipment=first(order,'equipment',[])
            key=first(equipment,'creator'),first(equipment,'version_name')
            if designs.get(key)!=first(equipment,'type'):problems.append(f'Unresolved starting production design: {key}')
    def order_identity(record):
        def canonical(block):
            return sorted((k,canonical(v) if isinstance(v,list) else v) for k,v in block if k!='type')
        return json.dumps([record['country'],canonical(record['order'])],sort_keys=True)
    if Counter(map(order_identity,original)) != Counter(map(order_identity,current)):
        problems.append('Starting shipyard orders differ in class, name, factories, progress, amount or manufacturer')
    return problems



def validate_designer_layouts(game=GAME):
    hulls, _ = equipment_database(game, ROOT)
    issues = []
    for path in (ROOT/'interface/equipmentdesigner/ships').glob('*.gui'):
        tree = parse(read(path))
        for window in walk(tree, 'containerWindowType'):
            name = first(window, 'name', '')
            if not str(name).startswith('equipment_designer_'):
                continue
            hull = str(name).removeprefix('equipment_designer_')
            if hull not in hulls:
                continue
            layout = next((w for w in walk(window, 'containerWindowType') if first(w,'name') == 'module_slots'), [])
            named = {first(w,'name') for w in walk(layout, 'containerWindowType')}
            for slot, _ in slots_for(hulls, hull):
                if slot not in named:
                    issues.append(f'{path.name}: missing designer slot {hull}/{slot}')
    gui = parse(read(ROOT/'interface/equipmentdesignerview.gui'))
    for block in walk(gui, 'containerWindowType'):
        if first(block, 'name') == 'stat_icons':
            names = {first(icon, 'name') for icon in walk(block, 'iconType')}
            for name in ('torpedo','light_gun','heavy_gun','anti_air','anti_sub'):
                if 'stat_icon_'+name not in names:
                    issues.append('equipmentdesignerview.gui: missing stat_icon_'+name)
    return issues


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-root', type=Path, default=GAME)
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.snapshot:
        snapshot()
        return
    result=validate_integration(args.game_root)
    result['issues'].extend(validate_designer_layouts(args.game_root))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))
    raise SystemExit(bool(result['issues']))


if __name__ == '__main__':
    main()
