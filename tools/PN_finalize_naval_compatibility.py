"""Finalize inherited history, carrier-air and singleton overrides after runtime checks."""
import copy
import json
import re
import subprocess
from pathlib import Path
import PN_validate_naval as n
from PN_convert_naval import named_blocks, convert, hull_for, technology_unlocks, set_value
from PN_import_vnr import render


def main():
    mp=n.ROOT/'docs/naval/PN_vnr_import_manifest.json';manifest=json.loads(n.read(mp))
    if manifest.get('runtime_compatibility_finalized'):raise SystemExit('Already finalized')
    # Rebuild suppression from the immutable pre-import revision, excluding nested
    # portrait navy blocks and retaining the outer units block and its land/air data.
    for entry in manifest['additional_overrides']:
        rel=entry['path']
        if 'Required original OOB path' not in entry['reason']:continue
        try:text=subprocess.check_output(['git','show','4f332c4:'+rel],stderr=subprocess.DEVNULL).decode('utf-8-sig')
        except subprocess.CalledProcessError:text=n.read(n.GAME/rel)
        spans=[(a,b) for a,b,v in named_blocks(text,'fleet')]+[(a,b) for a,b,v in named_blocks(text,'navy') if list(n.walk(v,'ship'))]
        for key in ('add_equipment_production','add_equipment_to_stockpile'):
            spans += [(a,b) for a,b,v in named_blocks(text,key) if any(str(n.first(x,'type','')).startswith(('ship_hull_','destroyer_','submarine_','battleship_','carrier_','light_cruiser_','heavy_cruiser_','battle_cruiser_')) for x in n.values(v,'equipment'))]
        spans=[(a,b) for a,b in spans if not any(x<=a and y>=b and (x,y)!=(a,b) for x,y in spans)]
        for a,b in sorted(spans,reverse=True):text=text[:a]+'\n# Navy supplied by PN_initialize_navy.\n'+text[b:]
        try:n.parse(text)
        except ValueError:
            # A source OOB containing exclusively naval content needs no residual
            # wrapper or instant_effect block after suppression.
            if not any(word in text for word in ('division =','air_wings =','division_template =')):text='# Navy and shipyard orders supplied by PN_initialize_navy.\n'
            else:raise
        (n.ROOT/rel).write_text(text,encoding='utf-8')
    # Initial carriers have not yet loaded when vanilla air history executes.
    air=[]
    for tag in ('ENG','FRA','JAP','USA'):
        for suffix in ('air_bba','air_legacy'):
            rel=f'history/units/{tag}_1936_{suffix}.txt';p=n.ROOT/rel
            source=p if p.exists() else n.GAME/rel
            if not source.exists():continue
            text=n.read(source);original=text
            for a,b,block in reversed(list(named_blocks(text,'air_wings'))):
                piece=text[a:b]
                for key,value in block:
                    if key and not str(key).isdigit() and isinstance(value,list):
                        for x,y,v in reversed(list(named_blocks(piece,key))):piece=piece[:x]+'\n# Carrier wing installed by the PN startup air OOB after its carrier.\n'+piece[y:]
                text=text[:a]+piece+text[b:]
            if text!=original:p.write_text(text,encoding='utf-8');air.append(rel)
    manifest['carrier_air_overrides']=air
    # Equipment bonus enums are explicit, not inferred from new equipment files.
    hulls,modules=n.equipment_database(n.GAME,n.ROOT)
    text=n.read(n.GAME/'common/script_enums.txt');a,b,enum=next(named_blocks(text,'script_enum_equipment_bonus_type'))
    extra=['ship_hull_civilian','auxiliary_ship']+[k for k in hulls if k.startswith(('vnr_ship_','PN_ship_'))]
    text=text[:b-1]+'\n\t# Project Northwind naval equipment\n'+''.join('\t'+k+'\n' for k in extra if k not in n.bare(enum))+text[b-1:]
    (n.ROOT/'common/script_enums.txt').write_text(text,encoding='utf-8');manifest['script_enum_override']='common/script_enums.txt'
    # Merge singleton ideas rather than declaring duplicate IDs in additive files.
    for source,base_name in [('common/ideas/_overwrite.txt','air_spirits.txt'),('common/ideas/_naval_treaty.txt','zzz_generic.txt')]:
        entry=next(e for e in manifest['files'] if e['source']==source);old=n.ROOT/entry['destination'];source_text=n.read(old if old.exists() else n.SOURCE/source);text=n.read(n.GAME/'common/ideas'/base_name)
        for group in n.values(n.parse(source_text),'ideas'):
            for category,body in group:
                for key,value in body:
                    if not isinstance(value,list):continue
                    a,b,v=next(named_blocks(source_text,key));raw=source_text[a:b]
                    spans=list(named_blocks(text,key))
                    if not spans:
                        x,y,v=next(named_blocks(text,category))
                        text=text[:y-1]+'\n'+raw+'\n'+text[y-1:]
                    for x,y,v in reversed(spans):text=text[:x]+raw+text[y:]
        destination=n.ROOT/'common/ideas'/base_name;destination.write_text(text,encoding='utf-8');old.unlink(missing_ok=True)
        entry.update(destination=destination.relative_to(n.ROOT).as_posix(),exception='Required original idea override: duplicate idea IDs are rejected',adaptation='Merge VNR idea changes with installed base-game definitions')
    for p in (n.GAME/'common/ai_equipment').glob('*naval.txt'):
        target=n.ROOT/'common/ai_equipment'/p.name;target.write_text('# Naval AI designs supplied by the PN_vnr_* templates.\n',encoding='utf-8')
    # Convert every inherited naval history design, including legacy CSA and no-MTG
    # design branches, using vanilla defaults as input and VNR modules as output.
    base_hulls,base_modules=n.equipment_database(n.GAME,n.GAME)
    legacy={'destroyer':'light','submarine':'submarine','battleship':'heavy','heavy_cruiser':'cruiser','light_cruiser':'cruiser','battle_cruiser':'heavy','carrier':'carrier'}
    unlocks=technology_unlocks(n.GAME,n.ROOT);records=[];changed=[]
    for directory in ('history/countries','common/special_projects/projects'):
        for rel,p in n.effective_files(n.GAME,n.ROOT,directory).items():
            text=n.read(p);original=text
            for a,b,design in reversed(list(named_blocks(text,'create_equipment_variant'))):
                old=n.first(design,'type','');match=re.fullmatch(r'('+'|'.join(legacy)+r')_([1-4])',str(old))
                if not str(old).startswith('ship_hull_') and not match:continue
                prepared=copy.deepcopy(design)
                if match:
                    family,level=match.groups()
                    target=f'ship_hull_{legacy[family]}_{level}'
                    if family=='carrier':target={'1':'ship_hull_carrier_conversion_bb','2':'ship_hull_carrier_1','3':'ship_hull_carrier_2','4':'ship_hull_carrier_3'}[level]
                    set_value(prepared,'type',target)
                    set_value(prepared,'modules',n.defaults_for(base_hulls,old))
                result,info=convert(prepared,hulls,modules)
                required=[info['hull']]+[v for v in info['modules'].values() if v!='empty'];techs=sorted({unlocks[x] for x in required if x in unlocks})
                raw=render([('set_technology',[(t,'1') for t in techs]+[('popup','no')]),('create_equipment_variant',result)])
                text=text[:a]+raw+text[b:];records.append(dict(file=directory+'/'+rel,name=n.first(design,'name'),original_type=old,**info))
            # Map all remaining references to removed doctrine IDs, including
            # add_sub_doctrine_progress fields rather than only direct assignments.
            for old,new in manifest['legacy_doctrine_mappings'].items():text=re.sub(r'(?<!\w)'+re.escape(old)+r'(?!\w)',new,text)
            if text!=original:
                destination=n.ROOT/directory/rel;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(text,encoding='utf-8');changed.append(destination.relative_to(n.ROOT).as_posix())
    # Translate project module unlocks to the equivalent active VNR modules.
    aliases={'ship_torpedo_sub_nuclear':'sub_nuclear_torpedo','ship_submarine_deck_space':'sub_airplane_launcher_2','ship_anechoic_tile':'anechoic_tile_1','big_ship_deck_space':'ship_deck_space_mega','ship_armor_ice_carrier_deck_1':'carrier_armor_deck','sub_ship_nuclear_engine_1':'sub_ship_engine_nuclear','heavy_ship_nuclear_engine_1':'heavy_ship_engine_nuclear','carrier_ship_nuclear_engine_1':'carrier_ship_engine_nuclear'}
    for filename in ('naval_projects.txt','nuclear_projects.txt'):
        p=n.ROOT/'common/special_projects/projects'/filename;text=n.read(p)
        for old,new in aliases.items():text=re.sub(r'(?<!\w)'+re.escape(old)+r'(?!\w)',new,text)
        p.write_text(text,encoding='utf-8')
    # link_numbering_with expects country tags, not another name-group ID.
    p=n.ROOT/'common/units/names_ships/PN_naval_compatibility_names.txt';text=n.read(p)
    for a,b,v in reversed(list(named_blocks(text,'link_numbering_with'))):
        if any(str(value).startswith('GER_THEME_') for key,value in v):text=text[:a]+text[b:]
    p.write_text(text,encoding='utf-8')
    manifest['inherited_history_overrides']=changed;manifest['runtime_compatibility_finalized']=True
    mp.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (n.ROOT/'docs/naval/PN_naval_inherited_designs.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
    print(f'Converted {len(records)} inherited/legacy history and project designs; {len(air)} deferred carrier-air files')


if __name__=='__main__':main()
