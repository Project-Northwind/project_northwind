"""Recorded compatibility repairs identified by static checks and the first game load."""
import copy
import json
from pathlib import Path
import re
import PN_validate_naval as n
from PN_import_vnr import render
from PN_convert_naval import named_blocks, set_value, hull_for


def replace_blocks(text, key, transform):
    for a,b,block in reversed(list(named_blocks(text,key))):
        updated=transform(block)
        if updated is not None:
            text=text[:a]+render([(key,updated)])+text[b:]
    return text


def main():
    manifest_path=n.ROOT/'docs/naval/PN_vnr_import_manifest.json'
    manifest=json.loads(n.read(manifest_path))
    if manifest.get('compatibility_repaired'):
        raise SystemExit('Repairs already applied')
    deviations=[]
    # PN_ sorts before the lowercase vanilla ship archetype files. Consolidate the
    # source equipment in its original dependency order and suppress originals.
    entries=[e for e in manifest['files'] if Path(e['source']).parent.as_posix()=='common/units/equipment' and e['source'].endswith('.txt')]
    combined=n.ROOT/'common/units/equipment/PN_naval_equipment.txt'
    chunks=[]
    for e in sorted(entries,key=lambda e:Path(e['source']).name):
        old=n.ROOT/e['destination']
        chunks.append('# Source section: '+e['source']+'\n'+n.read(old))
        old.unlink()
        if (n.GAME/e['source']).exists():
            suppression=n.ROOT/e['source']
            suppression.write_text('# Definitions consolidated in PN_naval_equipment.txt for deterministic archetype ordering.\n',encoding='utf-8')
            e['suppression_path']=e['source']
        e['destination']=combined.relative_to(n.ROOT).as_posix()
        e['exception']=None
        e['adaptation']='Consolidated in source filename order; original vanilla path suppressed where required'
    combined.write_text('\n\n'.join(chunks),encoding='utf-8')
    deviations.append('Consolidate naval equipment into PN_naval_equipment.txt in source dependency order; preserve exact-path suppression files.')
    # Static modifiers cannot be duplicated in an additive file.
    modifier_entry=next(e for e in manifest['files'] if e['source']=='common/modifiers/z_vnr_combat_modifiers.txt')
    old=n.ROOT/modifier_entry['destination']
    replacements=n.parse(n.read(old)); vanilla=n.read(n.GAME/'common/modifiers/00_static_modifiers.txt')
    for key,value in replacements:
        spans=list(named_blocks(vanilla,key))
        if spans:
            for a,b,existing in reversed(spans):vanilla=vanilla[:a]+render([(key,value)])+vanilla[b:]
        else:vanilla+='\n'+render([(key,value)])+'\n'
    destination=n.ROOT/'common/modifiers/00_static_modifiers.txt'
    destination.write_text(vanilla,encoding='utf-8');old.unlink()
    modifier_entry.update(destination=destination.relative_to(n.ROOT).as_posix(),exception='Required original file override: static modifiers reject duplicate IDs',adaptation='Merged VNR naval modifier changes into installed base-game static modifiers')
    # Entity clone targets must exist earlier in the same asset file.
    entity_entry=next(e for e in manifest['files'] if e['source']=='gfx/entities/z_vnr_ships.asset')
    old=n.ROOT/entity_entry['destination'];destination=n.ROOT/'gfx/entities/units_ships.asset'
    destination.write_text(n.read(n.GAME/'gfx/entities/units_ships.asset')+'\n'+n.read(old),encoding='utf-8');old.unlink()
    entity_entry.update(destination=destination.relative_to(n.ROOT).as_posix(),exception='Required original asset override: entity clone targets must load before clones',adaptation='Appended naval entity aliases after their vanilla clone targets')
    # Normalize noncanonical source paths before mapping them to renamed assets.
    paths={e['source']:e['destination'] for e in manifest['files'] if e['source'].startswith('gfx/')}
    for e in manifest['files']:
        p=n.ROOT/e['destination']
        if p.suffix not in ('.gfx','.gui','.asset','.txt') or not p.exists():continue
        text=n.read(p);original=text
        text=text.replace('srpiteType','spriteType')
        def canonical(match):
            value=re.sub(r'[/\\]+','/',match.group(1))
            return '"'+paths.get(value,value)+'"'
        text=re.sub(r'"(gfx[/\\][^"\n]+)"',canonical,text)
        if text!=original:p.write_text(text,encoding='utf-8')
    # Restore removed vanilla technology IDs used by inherited country/focus/event
    # scripts. Hidden compatibility techs retain their actual vanilla effects;
    # equipment unlocks are translated to active VNR hulls.
    known={}
    for p in n.effective_files(n.GAME,n.ROOT,'common/technologies').values():
        for group in n.values(n.parse(n.read(p)),'technologies'):
            known.update((k,v) for k,v in group if isinstance(v,list))
    compatibility=[]
    for name in ('MTG_naval.txt','MTG_naval_Support.txt','naval.txt'):
        for group in n.values(n.parse(n.read(n.GAME/'common/technologies'/name)),'technologies'):
            for key,spec in group:
                if key in known or not isinstance(spec,list):continue
                spec=copy.deepcopy(spec)
                spec[:]=[(k,v) for k,v in spec if k not in ('folder','path','dependencies','XOR')]
                set_value(spec,'allow',[('always','no')])
                eq=n.first(spec,'enable_equipments')
                if eq is not None:set_value(spec,'enable_equipments',[(k,hull_for(v) if isinstance(v,str) and v.startswith('ship_hull_') else v) for k,v in eq])
                compatibility.append((key,spec));known[key]=spec
    compatibility += [('basic_ballast_tank',[('research_cost','1'),('start_year','1914'),('allow',[('always','no')]),('enable_equipment_modules',[(None,'pressure_hull_1')])]),('gas_turbine',[('research_cost','1'),('start_year','1948'),('allow',[('always','no')])])]
    p=n.ROOT/'common/technologies/PN_naval_compatibility.txt'
    p.write_text('# Hidden compatibility IDs preserve inherited grants without restoring the vanilla naval tree.\n'+render([('technologies',compatibility)])+'\n',encoding='utf-8')
    deviations.append(f'Restored {len(compatibility)} hidden legacy technology IDs referenced by base-game and VNR content.')
    # Strip initial vanilla fleets before country loading. Empty VNR hull variants
    # are deliberately hidden, so loading them first creates missing-variant errors.
    suppressions=[]
    custom_paths={f'{tag}_1936_naval_mtg.txt' for tag in ('GRE','LAT','SOV','SWE','TUR','UKR')}
    for rel,p in n.effective_files(n.GAME,n.ROOT,'history/units').items():
        if Path(rel).name.startswith('PN_') or rel in custom_paths:continue
        text=n.read(p)
        if not re.search(r'\b(ship_hull_|destroyer_\d|battleship_\d|submarine_\d|carrier_\d|heavy_cruiser_\d|light_cruiser_\d|battle_cruiser_\d)',text):continue
        edited=text
        # Fleet and legacy navy blocks contain only naval formations.
        spans=[]
        for key in ('fleet','navy'):
            spans.extend((a,b) for a,b,block in named_blocks(text,key))
        for key in ('instant_effect',):
            pass
        # Naval production is installed from the VNR/custom OOB after startup.
        for key in ('add_equipment_production','add_equipment_to_stockpile'):
            spans.extend((a,b) for a,b,block in named_blocks(text,key) if any(str(n.first(x,'type','')).startswith(('ship_hull_','destroyer_','submarine_','battleship_','carrier_','light_cruiser_','heavy_cruiser_','battle_cruiser_')) for x in n.values(block,'equipment')))
        for a,b in sorted(spans,reverse=True):edited=edited[:a]+'# Navy supplied by PN_initialize_navy.'+edited[b:]
        if edited!=text:
            destination=n.ROOT/'history/units'/rel
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(edited,encoding='utf-8')
            suppressions.append(dict(path=destination.relative_to(n.ROOT).as_posix(),reason='Required original OOB path; suppress vanilla navy while preserving land and air units'))
    manifest['additional_overrides']=suppressions
    deviations.append(f'Suppressed initial vanilla naval blocks in {len(suppressions)} exact-path OOB overrides, preserving other units.')
    # Repair stale source designer slots, with explicit source-derived choices.
    for filename in ('PN_add_ai_variants.txt','PN_add_never_built.txt','PN_add_naval_variants.txt','PN_naval_starting_variants.txt'):
        path=n.ROOT/'common/scripted_effects'/filename
        def fix(design):
            hull=n.first(design,'type',''); name=n.first(design,'name');choices=n.first(design,'modules',[])
            if name=='Midway Class' and n.first(choices,'front_2_custom_slot')=='angled_deck':
                # The 1944 carrier lacks an angled-deck mount; preserve its deck
                # capacity rather than installing a module in an illegal slot.
                set_value(choices,'front_2_custom_slot','ship_deck_space_open')
            if name=='Object 71 Class':set_value(choices,'fixed_ship_secondaries_slot','dp_ship_secondaries_2_bb')
            if name=='Object 41/56 Class' and n.first(choices,'fixed_ship_fire_control_system_slot')=='ship_sonar_2':
                set_value(choices,'fixed_ship_fire_control_system_slot','ship_fire_control_system_3');set_value(choices,'fixed_ship_extra_electronics_slot','ship_sonar_2')
            if name in ('Kaidai VI Class','Porpoise Class','Grampus Class') and n.first(choices,'mid_1_custom_slot')=='sub_ship_periscope_1':
                choices[:]=[(k,v) for k,v in choices if k!='mid_1_custom_slot'];set_value(choices,'fixed_sub_periscope_slot','sub_ship_periscope_1')
            if name=='South Dakota Class' and n.first(choices,'front_1_custom_slot')=='ship_anti_air_1_h':set_value(choices,'front_1_custom_slot','ship_anti_air_1')
            if hull=='vnr_ship_hull_cruiser_coastal_defense_ship':
                if any(str(v).startswith('ship_heavy_battery_') for k,v in choices):set_value(choices,'fixed_ship_role_slot','ship_hull_cruiser_role_mo')
                elif n.first(choices,'fixed_ship_secondaries_slot','').startswith('ship_secondaries_'):
                    set_value(choices,'fixed_ship_secondaries_slot',n.first(choices,'fixed_ship_secondaries_slot')+'_light')
            return design
        path.write_text(replace_blocks(n.read(path),'create_equipment_variant',fix),encoding='utf-8')
    # Ensure source initial designs have their chassis unlocked, notably CHI Chen Hai.
    path=n.ROOT/'common/scripted_effects/PN_add_naval_variants.txt'
    text=n.read(path)
    from PN_convert_naval import technology_unlocks
    unlocks=technology_unlocks(n.GAME,n.ROOT)
    for a,b,design in reversed(list(named_blocks(text,'create_equipment_variant'))):
        hull=n.first(design,'type','')
        if hull in unlocks:text=text[:a]+'set_technology = { '+unlocks[hull]+' = 1 popup = no }\n'+text[a:b]+text[b:]
    path.write_text(text,encoding='utf-8')
    # Source completes projects already completed via technology on_research effects.
    path=n.ROOT/'common/scripted_effects/PN_add_starting_tech.txt'
    text=n.read(path)
    text=re.sub(r'(?m)^(\s*)complete_special_project\s*=\s*(sp:\w+)\s*$',lambda m:m.group(1)+'if = { limit = { NOT = { is_special_project_completed = '+m.group(2)+' } } complete_special_project = '+m.group(2)+' }',text)
    path.write_text(text,encoding='utf-8')
    # Keep the recorded Northwind conversion map synchronized with role corrections.
    path=n.ROOT/'docs/naval/PN_naval_conversion.json';conversion=json.loads(n.read(path))
    for d in conversion['designs']:
        if d['name']=='Erebus Class':
            d['role']='ship_hull_cruiser_role_mo';d['modules']['fixed_ship_role_slot']=d['role'];d['rationale']+=' Heavy-gun monitors use the VNR monitor role, which permits their batteries.'
    path.write_text(json.dumps(conversion,indent=2,ensure_ascii=False),encoding='utf-8')
    manifest['compatibility_repaired']=True;manifest['deviations']=deviations
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('\n'.join(deviations))


if __name__=='__main__':main()
