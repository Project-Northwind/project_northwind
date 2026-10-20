"""Convert inherited naval design rewards, production effects and event OOBs."""
import json
from pathlib import Path
import re
import PN_validate_naval as n
from PN_convert_naval import convert, hull_for, named_blocks, technology_unlocks
from PN_import_vnr import render


def main():
    output=n.ROOT/'docs/naval/PN_naval_rewards.json'
    if output.exists():raise SystemExit('Rewards already converted')
    hulls,modules=n.equipment_database(n.GAME,n.ROOT)
    unlocks=technology_unlocks(n.GAME,n.ROOT)
    mapping={old:hull_for(old) for old in hulls if old.startswith('ship_hull_') and hull_for(old) in hulls}
    pattern=re.compile(r'(?<!\w)('+ '|'.join(re.escape(k) for k in sorted(mapping,key=len,reverse=True))+r')(?!\w)')
    # The original ice-carrier project now unlocks the PN derivative of VNR's mega carrier.
    tech=n.ROOT/'common/technologies/PN_naval_compatibility.txt'
    content=n.read(tech).replace('vnr_ship_hull_mega_carrier','PN_ship_hull_ice_carrier')
    tech.write_text(content,encoding='utf-8')
    unlocks['PN_ship_hull_ice_carrier']='sp_ice_composite_runawayas'
    files=[];designs=[];writes=[]
    for directory in ('common/national_focus','common/scripted_effects','common/decisions','events'):
        for rel,path in n.effective_files(n.GAME,n.ROOT,directory).items():
            text=n.read(path);original=text
            for a,b,d in reversed(list(named_blocks(text,'create_equipment_variant'))):
                if not str(n.first(d,'type','')).startswith('ship_hull_'):continue
                converted,info=convert(d,hulls,modules)
                required=[info['hull']]+[v for v in info['modules'].values() if v!='empty']
                techs=sorted({unlocks[x] for x in required if x in unlocks})
                prefix=render([('set_technology',[(t,'1') for t in techs]+[('popup','no')])])+'\n'
                text=text[:a]+prefix+render([('create_equipment_variant',converted)])+text[b:]
                designs.append(dict(file=directory+'/'+rel,name=n.first(d,'name'),required_techs=techs,**info))
            text=pattern.sub(lambda match:mapping[match.group()],text)
            if text!=original:
                dest=n.ROOT/directory/rel;writes.append((dest,text));files.append(dest.relative_to(n.ROOT).as_posix())
    # Restore event/reward OOBs inadvertently caught by the initial fleet suppression
    # pass, then translate their equipment references. Keep test-only OOBs unmodified.
    manifest_path=n.ROOT/'docs/naval/PN_vnr_import_manifest.json';manifest=json.loads(n.read(manifest_path))
    kept=[]
    for e in manifest['additional_overrides']:
        rel=e['path'];name=Path(rel).name
        if '1936' not in name and '1939' not in name:
            if name.startswith('MTG_NAVAL_TEST_'):
                (n.ROOT/rel).unlink()
                continue
            text=pattern.sub(lambda match:mapping[match.group()],n.read(n.GAME/rel))
            writes.append((n.ROOT/rel,text));files.append(rel)
            e['reason']='Required original reward OOB path; restored ship formations with VNR hull references'
        kept.append(e)
    manifest['additional_overrides']=kept
    manifest['reward_overrides']=[dict(path=f,reason='Required exact path to replace inherited naval rewards without duplicate focus/event/effect IDs') for f in files if not Path(f).name.startswith('PN_')]
    for path,text in writes:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding='utf-8')
    output.write_text(json.dumps(dict(files=files,designs=designs),indent=2,ensure_ascii=False),encoding='utf-8')
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'Converted {len(designs)} naval rewards and hull references in {len(files)} effective files')


if __name__=='__main__':main()
