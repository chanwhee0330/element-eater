"""최종 PNG의 크기·잘림·동작 연결·보행·JSON 해시 회귀 검사."""
from pathlib import Path
import hashlib
import json
from PIL import Image
from torso_registration import fit_torso


def validate(assets, catalog):
    assets=Path(assets); errors=[]; count=0
    for element in catalog['elements']:
        sheets={state:Image.open(assets/element/f'hero-{element}-{state}.png').convert('RGBA')
                for state in ['idle','walk','attack','ingest']}
        for state,sheet in sheets.items():
            path=assets/element/f'hero-{element}-{state}.png'
            meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
            assert meta['sha256']==hashlib.sha256(path.read_bytes()).hexdigest(),path
            for row in range(4):
                feet=[]
                for col in range(8):
                    tile=sheet.crop((col*128,row*128,(col+1)*128,(row+1)*128))
                    fit=fit_torso(tile,element,catalog['torsoTarget'])
                    error=[abs(fit[k]-v) for k,v in zip(['cx','cy','rx','ry'],catalog['torsoTarget'])]
                    assert max(error)<=.6,(element,state,row,col,error)
                    errors.append(error);count+=1
                    bounds=tile.getchannel('A').point(lambda a:255 if a>=64 else 0).getbbox()
                    assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<128 and bounds[3]<128,(element,state,row,col,bounds)
                    if state in ['attack','ingest'] and col in [0,7]:
                        assert tile.tobytes()==sheets['idle'].crop((0,row*128,128,(row+1)*128)).tobytes(),(element,state,row,col,'idle endpoint')
                    feet.append(tile.crop((0,96,128,128)).tobytes())
                if state=='walk': assert len(set(feet))>=4,(element,row,'walking feet frozen')
    assert count==768,count
    print('Validated 768 exported frames; max center/radius errors:',
          [round(max(e[k] for e in errors),3) for k in range(4)],flush=True)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    validate(root/'assets/sprites/hero',json.loads((root/'outputs/previews/hero-elements/catalog.json').read_text(encoding='utf-8')))
