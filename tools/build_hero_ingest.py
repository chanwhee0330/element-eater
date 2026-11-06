from pathlib import Path
from statistics import median
from PIL import Image, ImageDraw, ImageFont
import argparse, base64, hashlib, io, json, math, shutil

parser=argparse.ArgumentParser()
parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--preview-dir',type=Path)
parser.add_argument('--assets-dir',type=Path)
parser.add_argument('--source',type=Path)
parser.add_argument('--template',type=Path)
args=parser.parse_args()
REPO=args.project_root.resolve()
HERO=REPO/'assets/sprites/hero/neutral'
OUT=(args.preview_dir or REPO/'outputs/previews/hero-neutral-ingest').resolve()
ASSETS=(args.assets_dir or HERO).resolve()
SOURCE=(args.source or HERO/'source/raster/ingest-source.png').resolve()
TEMPLATE=(args.template or REPO/'tools/hero_ingest_preview.html').resolve()
OUT.mkdir(parents=True,exist_ok=True);ASSETS.mkdir(parents=True,exist_ok=True)
(OUT/'orbs').mkdir(parents=True,exist_ok=True)
DIRS=['down','left','right','up']
NAMES=['정면','왼쪽','오른쪽','뒷면']
ELEMENTS={'water':'물','fire':'불','wind':'바람','earth':'흙','lightning':'번개'}
FPS=12;SIZE=128;PIVOT=(64,114);FOOT_BAND=108
MOUTHS={'down':(64,75),'left':(39,69),'right':(88,69),'up':(64,53)}
ORB_START={'down':(64,137),'left':(-11,73),'right':(139,73),'up':(64,0)}
FONT=lambda n:ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',n)
raw=Image.open(SOURCE).convert('RGBA')
idle=Image.open(HERO/'hero-neutral-idle.png').convert('RGBA')
assert raw.getpixel((0,0))[3]<32

def body_box(image):
    return image.getchannel('A').point(lambda v:255 if v>=128 else 0).getbbox()

def feet(image):
    box=body_box(image);height=box[3]-box[1];xs=[]
    a=image.getchannel('A')
    for y in range(round(box[3]-height*.085),box[3]):
        positions=[x for x in range(box[0],box[2]) if a.getpixel((x,y))>=128]
        if positions:xs.append((min(positions)+max(positions))/2)
    return (median(xs),box[3])

def uri(image):
    buf=io.BytesIO();image.save(buf,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()

atlas=Image.new('RGBA',(1024,512));packed={};frames={};animations={};registration={}
for row,direction in enumerate(DIRS):
    original=idle.crop((0,row*128,128,(row+1)*128))
    cells=[raw.crop((round(col*raw.width/8),round(row*raw.height/4),round((col+1)*raw.width/8),round((row+1)*raw.height/4))) for col in range(8)]
    reference=body_box(original);first=body_box(cells[0]);target=feet(original)
    scale=min((reference[2]-reference[0])/(first[2]-first[0]),(reference[3]-reference[1])/(first[3]-first[1]))
    # One uniform scale per direction. Only registration changes, never per-pose resizing.
    for cell in cells:
        box=body_box(cell);ax,ay=feet(cell)
        scale=min(scale,60/max(ax-box[0],1),60/max(box[2]-ax,1),110/max(ay-box[1],1))
    poses=[]
    for col,cell in enumerate(cells):
        box=body_box(cell);ax,ay=feet(cell)
        # Keep original RGBA within a padded rectangular crop; discard distant grid dust.
        trim=(max(0,box[0]-2),max(0,box[1]-2),min(cell.width,box[2]+2),min(cell.height,box[3]+2))
        clean=Image.new('RGBA',cell.size);clean.paste(cell.crop(trim),(trim[0],trim[1]))
        matrix=(1/scale,0,ax-target[0]/scale,0,1/scale,ay-target[1]/scale)
        pose=clean.transform((128,128),Image.Transform.AFFINE,matrix,Image.Resampling.BICUBIC)
        # Original soles stay identical, eliminating any position change at state boundaries.
        pose.paste(original.crop((0,FOOT_BAND,128,128)),(0,FOOT_BAND))
        if col in (0,7):pose=original.copy()
        assert pose.crop((0,FOOT_BAND,128,128)).tobytes()==original.crop((0,FOOT_BAND,128,128)).tobytes()
        assert pose.getbbox() and body_box(pose)[3]==reference[3]
        poses.append(pose);atlas.paste(pose,(col*128,row*128))
        key=f'{direction}_{col}'
        frames[key]={'frame':{'x':col*128,'y':row*128,'w':128,'h':128},'duration':1000/FPS,'pivotPixelsTopLeft':{'x':64,'y':114},'pico2dClip':{'left':col*128,'bottom':(3-row)*128,'width':128,'height':128},'mouthPixelsTopLeft':dict(zip(['x','y'],MOUTHS[direction]))}
    assert len({im.tobytes() for im in poses})>=6
    packed[direction]=poses
    animations[f'ingest_{direction}']={'frames':[f'{direction}_{i}' for i in range(8)],'fps':FPS,'loop':False,'next':'idle','events':[{'frame':4,'name':'consume_orb','once':True}]}
    registration[direction]={'uniformScale':scale,'fixedFeetFromY':FOOT_BAND,'targetFeetAnchor':list(target),'idleFirstAndLastExact':True}

atlas.save(ASSETS/'hero-neutral-ingest.png')
metadata={'schema':'element-eater.sprite-atlas.v1','image':'hero-neutral-ingest.png','imageSize':{'width':1024,'height':512},'state':'neutral','animationState':'ingest','frameSize':{'width':128,'height':128},'layout':{'rows':DIRS,'columns':8},'recommendedDrawScale':.5,'frames':frames,'animations':animations,'timing':{'fps':12,'durationSeconds':8/12,'consumeFrame':4,'consumeTimeSeconds':4/12,'status':'initial-animation-proposal'},'drawOrbBehindHero':['up'],'orbIsSeparate':True,'orbDiameterInPreviewPixels':24,'registration':registration,'sha256':hashlib.sha256((ASSETS/'hero-neutral-ingest.png').read_bytes()).hexdigest(),'generator':{'command':'python tools/build_hero_ingest.py','source':'source/raster/ingest-source.png'},'note':'F로 방출된 구슬을 먹는 무속성 애니메이션 시안. 본게임의 획득·변신·충돌은 미연결. 재생은 단발이고 완료 후 대기 자세로 돌아간다.'}
(ASSETS/'hero-neutral-ingest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')

orbs={}
for key in ELEMENTS:
    orb=Image.open(REPO/'assets/items/elements/break-release-v3/sprites'/f'{key}-orb.png').convert('RGBA')
    orb.save(OUT/'orbs'/f'{key}-orb.png');orbs[key]=orb

def action_at(t):
    start=.45;finish=start+8/FPS
    if t<start:return 0,0,'구슬 앞에서 대기'
    if t>=finish:return 7,None,'삼킨 뒤 대기 자세로 복귀'
    elapsed=t-start
    return min(7,int(elapsed*FPS+1e-6)),elapsed,'입 벌리기' if elapsed<2/FPS else '구슬 삼키기' if elapsed<5/FPS else '회복 자세'

def orb_pose(elapsed,direction):
    if elapsed is None or elapsed>=4/FPS:return None
    progress=max(0,min(1,(elapsed-1/FPS)/(2/FPS)))
    eased=progress*progress*(3-2*progress)
    a,b=ORB_START[direction],MOUTHS[direction]
    return (a[0]+(b[0]-a[0])*eased,a[1]+(b[1]-a[1])*eased,24*(1-progress*.9))

def draw_scene(direction,t,element='water',scale=2):
    frame,elapsed,label=action_at(t)
    result=Image.new('RGBA',(340,332))
    sprite=packed[direction][frame].resize((256,256),Image.Resampling.LANCZOS)
    origin=(42,28)
    orb=orb_pose(elapsed,direction)
    def draw_orb():
        if orb:
            x,y,size=orb;size=max(1,round(size*scale))
            art=orbs[element].resize((size,size),Image.Resampling.LANCZOS)
            result.alpha_composite(art,(round(origin[0]+x*scale-size/2),round(origin[1]+y*scale-size/2)))
    if direction=='up':draw_orb()
    result.alpha_composite(sprite,origin)
    if direction!='up':draw_orb()
    return result,label

def board(t,front_only=False):
    width=1400 if front_only else 1400
    image=Image.new('RGB',(width,490),'#14261e');d=ImageDraw.Draw(image)
    d.text((20,12),'무속성 주인공 · 원소 구슬 먹기',font=FONT(25),fill='#f6eed6')
    _,_,label=action_at(t);d.text((22,51),label,font=FONT(17),fill='#bdd2ae')
    entries=[('down',element,ELEMENTS[element]) for element in ELEMENTS] if front_only else [(direction,'water',NAMES[i]) for i,direction in enumerate(DIRS)]
    step=277 if front_only else 346
    for i,(direction,element,name) in enumerate(entries):
        x=12+i*step;w=268 if front_only else 336
        d.rounded_rectangle((x,89,x+w,476),radius=14,fill='#233e30',outline='#526a49')
        d.text((x+14,100),name,font=FONT(20),fill='#f4edcc')
        scene,_=draw_scene(direction,t,element)
        if front_only:
            scene=scene.resize((272,266),Image.Resampling.LANCZOS);image.paste(scene,(x-2,146),scene)
        else:image.paste(scene,(x-2,132),scene)
    return image

for name,front_only in [('hero-neutral-ingest.gif',False),('five-elements-ingest.gif',True)]:
    pictures=[board(i/24,front_only) for i in range(42)]
    pictures[0].save(OUT/name,save_all=True,append_images=pictures[1:],duration=[40,40,50,40,40,40]*7,loop=0,disposal=2,optimize=True)
board(.45+3/FPS).save(OUT/'preview-still.png')
contact=Image.new('RGB',(1024,512),'#203b30');contact.paste(atlas,(0,0),atlas);contact.save(OUT/'all-frames.png')

payload={'hero':uri(atlas),'idle':uri(idle),'orbs':{key:uri(orb) for key,orb in orbs.items()},'directions':DIRS,'mouths':MOUTHS,'starts':ORB_START}
template=TEMPLATE.read_text(encoding='utf-8')
template=template.replace('/* ASSET_DATA */',json.dumps(payload,ensure_ascii=False))
(OUT/'preview.html').write_text(template,encoding='utf-8')
print(json.dumps({'sheet':[1024,512],'frames':32,'fixedFeet':True,'exactIdleEndpoints':True,'directions':DIRS,'registration':registration},ensure_ascii=False))
