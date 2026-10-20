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
                pos += 1
                if pos >= len(tokens):
                    raise ValueError('Missing assignment value')
                value = tokens[pos]
                pos += 1
                result.append((unquote(token), block(True) if value == '{' else unquote(value)))
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
    if own is not None:
        return own
    parent = first(hulls[hull], 'parent') or first(hulls[hull], 'archetype')
    return inherited(hulls, parent, key, seen)


def check_design(design, hulls, modules):
    hull = first(design, 'type')
    if hull not in hulls:
        return [f'Unknown hull {hull}']
    slots = inherited(hulls, hull, 'module_slots') or []
    choices = first(design, 'modules', [])
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
    return problems


def check_ship(ship, designs):
    problems = []
    for hull, equipment in first(ship, 'equipment', []):
        owner, name = first(equipment, 'owner'), first(equipment, 'version_name')
        if designs.get((owner, name)) != hull:
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--game-root', type=Path, default=GAME)
    parser.add_argument('--snapshot', action='store_true')
    args = parser.parse_args()
    if args.snapshot:
        snapshot()
        return
    hulls, modules = equipment_database(args.game_root, ROOT)
    print(f'Effective equipment database: {len(hulls)} equipment, {len(modules)} modules')


if __name__ == '__main__':
    main()
