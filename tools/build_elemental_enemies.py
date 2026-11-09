"""고정 몸통과 관절 부품으로 무속성+5원소 적 12종의 36개 시트를 만듭니다."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/sprites/enemies/elemental-v1'
OUT=ROOT/'outputs/previews/elemental-enemies'
ELEMENTS={'neutral':'무속성','water':'물','fire':'불','wind':'바람','earth':'흙','lightning':'번개'}
TYPES={'melee':'근접형','ranged':'원거리형'}
STATES={'idle':('대기',6,True),'walk':('이동',10,True),'attack':('공격',12,False)}
DIRS=['down','left','right','up']
PARTS=['body','left_arm','right_arm','left_foot','right_foot']
SIZE=160
ROOT_PIVOT=(80,138)
BODY_CENTER=(80,86)
BODY_SIZE=(72,64)
ATTACK=[0,-.15,-.3,1,.65,.2,0,0]


def uri(path,mime='image/png'):
    return f'data:{mime};base64,'+base64.b64encode(Path(path).read_bytes()).decode('ascii')


def row_bands(image):
    a=np.asarray(image.getchannel('A'))
    ys=np.flatnonzero((a>=32).sum(axis=1)>20)
    cuts=np.flatnonzero(np.diff(ys)>1)
    bands=[list(map(int,b)) for b in zip(np.r_[ys[0],ys[cuts+1]],np.r_[ys[cuts]+1,ys[-1]+1])]
    while len(bands)>5:
        i=min(range(len(bands)-1),key=lambda i:bands[i+1][0]-bands[i][1])
        bands[i:i+2]=[[bands[i][0],bands[i+1][1]]]
    assert len(bands)==5,bands
    return [(max(0,a-5),min(image.height,b+5)) for a,b in bands]


def trim(image):
    b=image.getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox()
    assert b
    b=(max(0,b[0]-2),max(0,b[1]-2),min(image.width,b[2]+2),min(image.height,b[3]+2))
    return image.crop(b)


def register_body(image):
    a=np.asarray(image.getchannel('A'))>=180
    spans=[]
    for y in range(image.height):
        xs=np.flatnonzero(a[y])
        if len(xs):spans.append((y,int(xs[0]),int(xs[-1])+1))
    max_width=max(r-l for y,l,r in spans)
    wide=[(y,l,r) for y,l,r in spans if r-l>=max_width*.82]
    cx=float(np.median([(l+r)/2 for y,l,r in wide]))
    cy=(min(y for y,l,r in wide)+max(y for y,l,r in wide))/2
    bottom=max(y for y,l,r in spans)+1
    sx=max_width/BODY_SIZE[0];sy=(bottom-cy)/(BODY_SIZE[1]/2)
    registered=image.transform((SIZE,SIZE),Image.Transform.AFFINE,
        (sx,0,cx-sx*BODY_CENTER[0],0,sy,cy-sy*BODY_CENTER[1]),Image.Resampling.BICUBIC)
    bounds=registered.getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox()
    assert bounds[0]>2 and bounds[1]>2 and bounds[2]<SIZE-2 and bounds[3]<SIZE-2,bounds
    return registered,{'sourceCenter':[cx,cy],'sourceScale':[1/sx,1/sy],
                       'targetCenter':list(BODY_CENTER),'targetSize':list(BODY_SIZE)}


def resize_part(image,max_size):
    image=trim(image);scale=min(max_size[0]/image.width,max_size[1]/image.height)
    return image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.LANCZOS)


def emission_mask(body,element):
    p=np.asarray(body);r,g,b=p[:,:,:3].astype(float).transpose(2,0,1)
    masks={'neutral':(r>210)&(g>190)&(b>140)&(r>g*1.01)&(g>b*1.01),
           'water':(g>140)&(g>r*1.3)&(b>r*1.6),
           'fire':(r>180)&(g>90)&(b<100),
           'wind':(g>150)&(r>120)&(g>r*.95)&(b>60),
           'earth':(r>190)&(g>130)&(b<110),
           'lightning':(r>200)&(g>160)&(b<90)}
    return masks[element]&(p[:,:,3]>128)


def prepare_rigs(element,kind):
    source=Image.open(ASSETS/f'source/{element}-{kind}-parts.png').convert('RGBA')
    bands=row_bands(source);folder=ASSETS/element/kind/'rig';folder.mkdir(parents=True,exist_ok=True)
    rigs=[];records=[]
    for col,direction in enumerate(DIRS):
        parts={}
        for row,name in enumerate(PARTS):
            tile=source.crop((round(col*source.width/4),bands[row][0],round((col+1)*source.width/4),bands[row][1]))
            if name=='body':parts[name],record=register_body(tile)
            else:
                size=(36,46) if kind=='melee' and 'arm' in name else (25,36) if 'arm' in name else (26,20)
                parts[name]=resize_part(tile,size)
            parts[name].save(folder/f'{direction}-{name}.png')
        for side in ['left','right']:
            foot=parts[side+'_foot']
            cuff=foot.crop((round(foot.width*.3),round(foot.height*.18),round(foot.width*.7),round(foot.height*.58)))
            parts[side+'_leg']=cuff.resize((8,18),Image.Resampling.LANCZOS)
            parts[side+'_leg'].save(folder/f'{direction}-{side}_leg.png')
        parts['glow']=emission_mask(parts['body'],element)
        Image.fromarray((parts['glow']*255).astype('uint8')).save(folder/f'{direction}-emission-mask.png')
        rigs.append(parts);records.append(record)
    (folder/'registration.json').write_text(json.dumps({'sourceBands':bands,'directions':dict(zip(DIRS,records)),
        'root':list(ROOT_PIVOT),'bodyCenter':list(BODY_CENTER),'bodySize':list(BODY_SIZE)},ensure_ascii=False,indent=2),encoding='utf-8')
    return rigs


def put_arm(layer,part,joint,angle):
    padded=Image.new('RGBA',(80,80));padded.alpha_composite(part,(40-part.width//2,16-round(part.height*.13)))
    rotated=padded.rotate(angle,Image.Resampling.BICUBIC,center=(40,16))
    layer.alpha_composite(rotated,(round(joint[0]-40),round(joint[1]-16)))


def render_pose(rig,kind,direction,state,frame):
    phase=math.tau*frame/8
    attack=ATTACK[frame] if state=='attack' else 0
    arms=Image.new('RGBA',(SIZE,SIZE));feet=Image.new('RGBA',(SIZE,SIZE))
    far=Image.new('RGBA',(SIZE,SIZE));near=Image.new('RGBA',(SIZE,SIZE))
    # 몸통·머리·장식은 절대로 이동/회전/확대하지 않습니다.
    body=rig['body'].copy();pixels=np.array(body)
    pulse=.12*math.sin(phase) if state in ['idle','walk'] else max(0,attack)*.45
    colors=pixels[:,:,:3].astype(float);mask=rig['glow']
    colors[mask]=np.clip(colors[mask]*(1+pulse),0,255)
    pixels[:,:,:3]=np.rint(colors).astype('uint8');body=Image.fromarray(pixels)
    slots={'down':[(46,87),(114,87)],'up':[(46,87),(114,87)],
           'left':[(72,82),(86,90)],'right':[(74,90),(88,82)]}[direction]
    vector={'down':(0,1),'left':(-1,0),'right':(1,0),'up':(0,-1)}[direction]
    for index,name in enumerate(['left_arm','right_arm']):
        sign=1 if index==0 else -1
        angle=sign*3*math.sin(phase) if state=='idle' else sign*13*math.sin(phase) if state=='walk' else sign*attack*(27 if kind=='melee' else 15)
        reach=attack*(14 if kind=='melee' and index==1 else 3)
        joint=(slots[index][0]+vector[0]*reach,slots[index][1]+vector[1]*reach)
        is_far=direction=='up' or direction=='left' and index==0 or direction=='right' and index==1
        put_arm(far if is_far else near,rig[name],joint,angle)
    for index,name in enumerate(['left_foot','right_foot']):
        sign=1 if index==0 else -1
        lift=max(0,math.sin(phase)*sign)*5 if state=='walk' else 0
        stride=math.sin(phase)*sign*4 if state=='walk' and direction in ['left','right'] else 0
        x=[64,96][index] if direction in ['down','up'] else [73,88][index]
        leg=rig[['left_leg','right_leg'][index]]
        feet.alpha_composite(leg,(round(x+stride-4),111))
        part=rig[name];feet.alpha_composite(part,(round(x+stride-part.width/2),round(ROOT_PIVOT[1]-lift-part.height)))
    result=Image.new('RGBA',(SIZE,SIZE));result.alpha_composite(feet);result.alpha_composite(far)
    result.alpha_composite(body);result.alpha_composite(near)
    arms.alpha_composite(far);arms.alpha_composite(near);arms.alpha_composite(feet)
    return result,body,arms


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    catalog={'schema':'element-eater.elemental-enemies.v1','frameSize':SIZE,'root':list(ROOT_PIVOT),
             'bodyCenter':list(BODY_CENTER),'bodySize':list(BODY_SIZE),'directions':DIRS,
             'elementCount':5,'appearanceCount':len(ELEMENTS),'behaviorTypeCount':2,
             'sheetCount':len(ELEMENTS)*len(TYPES)*len(STATES),'frameCount':len(ELEMENTS)*len(TYPES)*len(STATES)*32,'elements':{}}
    for element,label in ELEMENTS.items():
        catalog['elements'][element]={'name':label,'isElemental':element!='neutral','types':{}}
        for kind,kind_label in TYPES.items():
            folder=ASSETS/element/kind;rigs=prepare_rigs(element,kind)
            poses={state:[] for state in STATES}
            for row,direction in enumerate(DIRS):
                rows={state:[] for state in STATES};occupied=np.zeros((SIZE,SIZE),dtype=bool)
                for state in STATES:
                    for frame in range(8):
                        image,body,limbs=render_pose(rigs[row],kind,direction,state,frame)
                        assert body.getchannel('A').tobytes()==rigs[row]['body'].getchannel('A').tobytes()
                        rows[state].append(image);occupied|=np.asarray(limbs.getchannel('A'))>0
                rows['attack'][0]=rows['idle'][0].copy();rows['attack'][7]=rows['idle'][0].copy()
                body=np.asarray(rigs[row]['body']);protected=(body[:,:,3]>=240)&~rigs[row]['glow']&~occupied
                assert protected.sum()>1000,(element,kind,direction,int(protected.sum()))
                Image.fromarray((protected*255).astype('uint8')).save(folder/f'rig/{direction}-body-lock-mask.png')
                for state in STATES:poses[state].append(rows[state])
            entry={'name':kind_label,'states':{},'muzzle':{'down':[80,106],'left':[45,99],'right':[115,99],'up':[80,65]}}
            for state,(state_label,fps,loop) in STATES.items():
                sheet=Image.new('RGBA',(SIZE*8,SIZE*4));frames={}
                for row,direction in enumerate(DIRS):
                    for frame,image in enumerate(poses[state][row]):
                        sheet.paste(image,(frame*SIZE,row*SIZE))
                        frames[f'{direction}_{frame}']={'frame':{'x':frame*SIZE,'y':row*SIZE,'w':SIZE,'h':SIZE},
                            'duration':1000/fps,'pivotPixelsTopLeft':{'x':80,'y':138},
                            'pico2dClip':{'left':frame*SIZE,'bottom':(3-row)*SIZE,'width':SIZE,'height':SIZE}}
                name=f'enemy-{element}-{kind}-{state}.png';path=folder/name;sheet.save(path)
                meta={'schema':'element-eater.sprite-atlas.v1','image':name,'imageSize':{'width':SIZE*8,'height':SIZE*4},
                    'element':element,'isElemental':element!='neutral','behaviorType':kind,'animationState':state,'frameSize':{'width':SIZE,'height':SIZE},
                    'layout':{'rows':DIRS,'columns':8},'fps':fps,'loop':loop,'recommendedDrawScale':.5,
                    'registration':{'method':'fixed-torso-articulated-parts','root':list(ROOT_PIVOT),'bodyCenter':list(BODY_CENTER),
                        'bodySize':list(BODY_SIZE),'perFrameBodyTransform':False,'bodyAlphaInvariant':True,
                        'protectedBodyPixelsExact':True,'bodyGeometryChanges':0},
                    'attackTiming':{'eventFrame':3,'status':'initial-animation-proposal'},'combatImplemented':False,
                    'frames':frames,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'generator':{'command':'python tools/build_elemental_enemies.py','source':f'../../source/{element}-{kind}-parts.png'}}
                path.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
                entry['states'][state]={'image':f'{element}/{kind}/{name}','fps':fps,'loop':loop,'label':state_label}
            catalog['elements'][element]['types'][kind]=entry
            print('Built '+element+' '+kind,flush=True)
    (ASSETS/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    validate(catalog)
    return catalog


def validate(catalog):
    count=0
    for element,element_entry in catalog['elements'].items():
        for kind,entry in element_entry['types'].items():
            sheets={state:Image.open(ASSETS/data['image']).convert('RGBA') for state,data in entry['states'].items()}
            for row,direction in enumerate(DIRS):
                body=np.asarray(Image.open(ASSETS/element/kind/f'rig/{direction}-body.png').convert('RGBA'))
                mask=np.asarray(Image.open(ASSETS/element/kind/f'rig/{direction}-body-lock-mask.png'))>0
                assert mask.sum()>1000
                for state,sheet in sheets.items():
                    frames=[]
                    for i in range(8):
                        tile=sheet.crop((i*SIZE,row*SIZE,(i+1)*SIZE,(row+1)*SIZE));p=np.asarray(tile)
                        assert np.array_equal(p[mask],body[mask]),(element,kind,state,direction,i,'body drift')
                        bounds=tile.getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox()
                        assert bounds[0]>0 and bounds[1]>0 and bounds[2]<SIZE and bounds[3]<SIZE,(element,kind,state,direction,i,bounds)
                        frames.append(p);count+=1
                    assert np.any(frames[0]!=frames[2]),(element,kind,state,direction,'static loop')
                    if state=='walk':assert np.any(frames[0][120:]!=frames[2][120:]),(element,kind,direction,'frozen feet')
                    if state=='attack':
                        idle=sheets['idle'].crop((0,row*SIZE,SIZE,(row+1)*SIZE))
                        assert frames[0].tobytes()==idle.tobytes() and frames[7].tobytes()==idle.tobytes()
            for data in entry['states'].values():
                path=ASSETS/data['image'];meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
                assert meta['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert count==catalog['frameCount']==len(ELEMENTS)*len(TYPES)*len(STATES)*32,count
    print(f'Validated {count} exported frames: body pixels fixed, real limb motion, endpoints, bounds and hashes.',flush=True)


def render_previews(catalog):
    OUT.mkdir(parents=True,exist_ok=True);font=lambda n:ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',n)
    sheets={};embedded={}
    for el,e in catalog['elements'].items():
        for kind,k in e['types'].items():
            for state,s in k['states'].items():
                sheets[el,kind,state]=Image.open(ASSETS/s['image']).convert('RGBA');embedded[s['image']]=uri(ASSETS/s['image'])
    def board(t,kind):
        image=Image.new('RGB',(790,110+len(ELEMENTS)*185),'#14261e');d=ImageDraw.Draw(image)
        d.text((18,12),'일반 적 · '+TYPES[kind]+' · 몸통 크기/중심 고정',font=font(24),fill='#f4edd5')
        for col,(state,(label,_,_)) in enumerate(STATES.items()):d.text((136+col*216,56),label,font=font(18),fill='#c7d9b3')
        for row,(el,label) in enumerate(ELEMENTS.items()):
            y=88+row*185;d.text((12,y+67),label,font=font(18),fill='#e7e1c4')
            for col,(state,(_,fps,loop)) in enumerate(STATES.items()):
                x=90+col*216;d.rounded_rectangle((x,y,x+203,y+174),radius=12,fill='#233e30',outline='#48674b')
                phase=t%2
                active=state!='attack' or .4<=phase<.4+8/12
                frame=int(t*fps)%8 if loop else min(7,int((phase-.4)*12)) if active else 0
                tile=sheets[el,kind,state if active else 'idle'].crop((frame*SIZE,0,(frame+1)*SIZE,SIZE))
                image.paste(tile,(x+20,y+4),tile)
        return image
    for kind in TYPES:
        pictures=[board(i/20,kind) for i in range(40)];palette=pictures[13].quantize(colors=256)
        pictures=[p.quantize(palette=palette,dither=Image.Dither.NONE) for p in pictures]
        pictures[0].save(OUT/f'{kind}.gif',save_all=True,append_images=pictures[1:],duration=50,loop=0,disposal=2)
        board(.65,kind).save(OUT/f'{kind}-still.png')
    data={'catalog':catalog,'images':embedded}
    projectile_root=ROOT/'assets/effects/basic-projectiles/v1'
    data['projectiles']={el:uri(projectile_root/f'{el}-flight.png') for el in ELEMENTS if (projectile_root/f'{el}-flight.png').exists()}
    html=(ROOT/'tools/elemental_enemies_preview.html').read_text(encoding='utf-8')
    html=html.replace('/* DATA */',json.dumps(data,ensure_ascii=False,separators=(',',':')))
    html=html.replace('/* MELEE_FALLBACK */',uri(OUT/'melee.gif','image/gif')).replace('/* RANGED_FALLBACK */',uri(OUT/'ranged.gif','image/gif'))
    (OUT/'preview.html').write_text(html,encoding='utf-8')
    print('Rendered enemy HTML and GIFs.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--render-only',action='store_true');parser.add_argument('--validate-only',action='store_true');args=parser.parse_args()
    if args.render_only or args.validate_only:catalog=json.loads((ASSETS/'catalog.json').read_text(encoding='utf-8'));validate(catalog)
    else:catalog=build()
    if not args.validate_only:
        render_previews(catalog)
        from build_animation_gallery import main
        main()
