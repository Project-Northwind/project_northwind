"""Adapt the imported VNR loader to Northwind's once-only startup."""
import json
from pathlib import Path
import PN_validate_naval as n
from PN_import_vnr import render
from PN_convert_naval import named_blocks, CUSTOM, set_value


def main():
    target = n.ROOT/'common/scripted_effects/PN_naval_initialization.txt'
    if target.exists():
        raise SystemExit('Startup already integrated')
    event_path=n.ROOT/'events/PN_00_navy_rework.txt'
    text=n.read(event_path)
    start,end,body=next(named_blocks(text,'immediate'))
    for tag in CUSTOM:
        set_value(body,tag,[('load_oob',f'PN_{tag}_1936_naval')])
    # Delete only pre-existing vanilla fleets, before any PN fleets are loaded.
    # A global guard surrounds the entire sequence, including cleanup and bonuses.
    body += [('set_global_flag','vnr_oob_loaded'),('set_global_flag','PN_naval_initialized')]
    target.write_text('# Once-only migration: technologies/designs already called from country history; replace initial vanilla fleets, then load PN fleets.\n'+render([('PN_initialize_navy',[('if',[('limit',[('NOT',[('has_global_flag','PN_naval_initialized')])])]+body)])])+'\n',encoding='utf-8')
    event_path.write_text(text[:start]+'immediate = { PN_initialize_navy = yes }'+text[end:],encoding='utf-8')
    # The event remains a compatible wrapper; the splash is informational only.
    gui_path=n.ROOT/'common/scripted_guis/PN_00_navy_rework_welcome_splash_gui.txt'
    gui=n.read(gui_path)
    a,b,click=next(named_blocks(gui,'navy_rework_options_button_click'))
    click=[(k,v) for k,v in click if k!='if']
    gui_path.write_text(gui[:a]+render([('navy_rework_options_button_click',click)])+gui[b:],encoding='utf-8')
    original=n.ROOT/'common/on_actions/PN_00_navy_rework.txt'
    actions=n.parse(n.read(original))
    effect=n.first(n.first(n.first(actions,'on_actions'),'on_startup'),'effect')
    effect[:]=[(k,v) for k,v in effect if k!='GDC']
    effect += [('random_country',[('limit',[('is_ai','no')]),('PN_initialize_navy','yes')]),('if',[('limit',[('NOT',[('has_global_flag','PN_naval_initialized')])]),('random_country',[('PN_initialize_navy','yes')])])]
    startup=n.ROOT/'common/on_actions/PN_naval_startup.txt'
    startup.write_text('# Project Northwind naval startup; also works in all-AI/observer games.\n'+render(actions)+'\n',encoding='utf-8')
    original.unlink()
    # GDC is an external-mod assumption; Guangzhou belongs to CHI in base HOI4.
    strategy=n.ROOT/'common/ai_strategy/PN_vnr_naval_strategy.txt'
    strategy.write_text(n.read(strategy).replace('GDC','CHI'),encoding='utf-8')
    manifest_path=n.ROOT/'docs/naval/PN_vnr_import_manifest.json'
    manifest=json.loads(n.read(manifest_path))
    for entry in manifest['files']:
        if entry['destination']==original.relative_to(n.ROOT).as_posix():
            entry['destination']=startup.relative_to(n.ROOT).as_posix()
            entry['adaptation']='Northwind guarded initialization; no external GDC access grant'
    # replace_path excludes all vanilla AI templates, allowing consistent PN filenames.
    for entry in manifest['files']:
        path=Path(entry['destination'])
        if path.parts[:2]==('common','ai_navy') and len(path.parts)>3 and path.parts[2] in ('fleet','goals','taskforce') and not path.name.startswith('PN_'):
            new=path.with_name('PN_'+path.name)
            (n.ROOT/path).rename(n.ROOT/new)
            entry['destination']=new.as_posix()
            entry['exception']=None
            entry['adaptation']='PN filename under replaced naval AI directory'
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    descriptor=n.ROOT/'descriptor.mod'
    content=n.read(descriptor)
    for kind in ('fleet','goals','taskforce'):
        declaration=f'replace_path="common/ai_navy/{kind}"'
        if declaration not in content:
            content+='\n'+declaration+'\n'
    descriptor.write_text(content,encoding='utf-8')
    # Avoid exposing a start that the source overhaul does not support.
    bookmark=n.ROOT/'common/bookmarks/blitzkrieg.txt'
    bookmark.parent.mkdir(parents=True,exist_ok=True)
    bookmark.write_text('# Project Northwind embedded naval overhaul supports fresh 1936 games.\n# Suppress the inherited unsupported 1939 bookmark.\n',encoding='utf-8')
    print('Northwind startup integrated; 1936 bookmark supported, inherited 1939 bookmark suppressed')


if __name__=='__main__':
    main()
