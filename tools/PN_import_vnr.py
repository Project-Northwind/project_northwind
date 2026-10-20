"""Import a pinned local VNR snapshot; never overwrite Northwind collisions blindly."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import PN_validate_naval as n


def render(block, depth=0):
    lines = []
    for key, value in block:
        head = '' if key is None else str(key) + ' ' + getattr(key, 'operator', '=') + ' '
        if isinstance(value, list):
            lines.extend(['\t' * depth + head + '{', render(value, depth + 1), '\t' * depth + '}'])
        else:
            value = str(value)
            if not value or re.search(r'\s|[{}#"]', value):
                value = '"' + value.replace('"', '\\"') + '"'
            lines.append('\t' * depth + head + value)
    return '\n'.join(lines)


def main():
    manifest_path = n.ROOT / 'docs/naval/PN_vnr_import_manifest.json'
    if manifest_path.exists():
        raise SystemExit('Already imported; use manifest for maintenance, not blind re-import')
    entries, path_map, oob_map = [], {}, {}
    source_files = [p for p in n.SOURCE.rglob('*') if p.is_file() and p.relative_to(n.SOURCE).parts[0] in ('common', 'events', 'gfx', 'history', 'interface', 'localisation')]
    names = set()
    for p in (n.ROOT / 'common/units/names_ships').glob('*.txt'):
        names.update(k for k, v in n.parse(n.read(p)) if k)
    for src in source_files:
        rel = src.relative_to(n.SOURCE)
        exact = (n.GAME / rel).is_file()
        exception = 'Required original path to override base-game file' if exact else None
        dst_rel = rel if exact else rel.with_name('PN_' + rel.name.lstrip('_'))
        if (n.ROOT / rel).exists():
            if 'names_ships' not in rel.parts:
                raise ValueError(f'Unresolved Northwind collision: {rel}')
            dst_rel = rel.with_name('PN_naval_' + rel.name)
            exception = None
        path_map[rel.as_posix()] = dst_rel.as_posix()
        if rel.parts[:2] == ('history', 'units'):
            oob_map[rel.stem] = dst_rel.stem
        entries.append(dict(source=rel.as_posix(), destination=dst_rel.as_posix(), sha256=hashlib.sha256(src.read_bytes()).hexdigest(), exception=exception))
    replacements = {k: v for k, v in path_map.items() if k != v}
    # Paths first, then OOB identifiers; match whole identifiers to avoid suffix damage.
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True)))
    oob_pattern = re.compile(r'(?<![\w])(' + '|'.join(re.escape(k) for k in oob_map) + r')(?![\w])')
    for entry in entries:
        src, dst = n.SOURCE / entry['source'], n.ROOT / entry['destination']
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in ('.txt', '.gui', '.gfx', '.lua', '.yml', '.asset'):
            content = n.read(src)
            content = pattern.sub(lambda m: replacements[m.group()], content)
            content = oob_pattern.sub(lambda m: oob_map[m.group()], content)
            if 'names_ships' in src.parts:
                tree = n.parse(content)
                tree = [(k, v) for k, v in tree if k not in names]
                content = '# VNR name groups absent from Northwind; Northwind groups take precedence.\n' + render(tree) + '\n'
                entry['adaptation'] = 'Preserved Northwind name groups; imported only missing groups'
            dst.write_text(content, encoding='utf-8-sig' if src.suffix == '.yml' else 'utf-8')
        else:
            shutil.copyfile(src, dst)
    manifest_path.write_text(json.dumps(dict(source_version='v3.3 - Das Boot', retained_ids='Equipment, modules, technologies, original VNR script and graphics IDs retained as compatibility interfaces; new Northwind integration uses PN names.', files=entries), indent=2), encoding='utf-8')
    print(f'Imported {len(entries)} files; {sum(bool(e["exception"]) for e in entries)} exact-path overrides')


if __name__ == '__main__':
    main()
