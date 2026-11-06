"""Pack ImageGen-created elemental hero animation atlases without redrawing art."""
from pathlib import Path
from statistics import median
from collections import deque
from PIL import Image, ImageDraw, ImageFont
import argparse, hashlib, json, math, os

parser=argparse.ArgumentParser()
parser.add_argument('--project-root',type=Path,default=Path(__file__).resolve().parents[1])
parser.add_argument('--output-dir',type=Path)
parser.add_argument('--assets-dir',type=Path)
parser.add_argument('--source-dir',type=Path)
parser.add_argument('--template',type=Path)
parser.add_argument('--report',type=Path)
args=parser.parse_args()
PROJECT=args.project_root.resolve()
OUT=(args.output_dir or PROJECT/'outputs/previews/hero-elements').resolve()
ASSETS=(args.assets_dir or PROJECT/'assets/sprites/hero').resolve()
SOURCE=(args.source_dir or PROJECT/'assets/sprites/hero/elemental-source-v1').resolve()
TEMPLATE=(args.template or PROJECT/'tools/hero_elements_preview.html').resolve()
OUT.mkdir(parents=True,exist_ok=True);ASSETS.mkdir(parents=True,exist_ok=True);(OUT/'previews').mkdir(exist_ok=True);(OUT/'orbs').mkdir(exist_ok=True)
ELEMENTS={'water':'물','fire':'불','wind':'바람','earth':'흙','lightning':'번개'}
STATES={'idle':('대기',4,True),'walk':('걷기',10,True),'attack':('기본 공격',12,False),'ingest':('구슬 먹기',12,False)}
DIRS=['down','left','right','up'];DIR_NAMES=['정면','왼쪽','오른쪽','뒷면']
SIZE=128;PIVOT=(64,114);FOOT_BAND=108
FONT=lambda n:ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',n)
neutral=Image.open(PROJECT/'assets/sprites/hero/neutral/hero-neutral-idle.png').convert('RGBA')

def measure(cell):
    a=cell.getchannel('A');width,height=a.size;pixels=list(a.get_flattened_data()) if hasattr(a,'get_flattened_data') else list(a.getdata());seen=bytearray(width*height);best=[]
    for index,value in enumerate(pixels):
        if value<128 or seen[index]:continue
        seen[index]=1;q=deque([index]);component=[]
        while q:
            at=q.popleft();component.append(at);x,y=at%width,at//width
            for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                if 0<=nx<width and 0<=ny<height:
                    next_at=ny*width+nx
                    if not seen[next_at] and pixels[next_at]>=128:seen[next_at]=1;q.append(next_at)
        if len(component)>len(best):best=component
    assert best,'empty sprite'
    xs=[point%width for point in best];ys=[point//width for point in best]
    body=(min(xs),min(ys),max(xs)+1,max(ys)+1)
    foot_rows={}
    for point in best:
        y=point//width
        if y>=body[3]-max(4,round((body[3]-body[1])*.08)):foot_rows.setdefault(y,[]).append(point%width)
    anchor=(median((min(row)+max(row))/2 for row in foot_rows.values()),body[3])
    # A padded rectangular crop preserves original alpha and excludes grid-edge dust.
    full=a.point(lambda v:255 if v>=96 else 0).getbbox()
    trim=(max(0,full[0]-2),max(0,full[1]-2),min(width,full[2]+2),min(height,full[3]+2))
    return {'image':cell,'body':body,'anchor':anchor,'trim':trim}

def read_source(path):
    image=Image.open(path).convert('RGBA')
    assert image.getchannel('A').getextrema()[0]==0,(path,'no alpha')
    assert image.getpixel((0,0))[3]<64,(path,'opaque background')
    rows=[]
    for row in range(4):
        frames=[]
        for col in range(8):
            box=(round(col*image.width/8),round(row*image.height/4),round((col+1)*image.width/8),round((row+1)*image.height/4))
            frames.append(measure(image.crop(box)))
        rows.append(frames)
    return rows

def pack_pose(data,scale):
    image=data['image'];x0,y0,x1,y1=data['trim'];ax,ay=data['anchor']
    clean=Image.new('RGBA',image.size);clean.paste(image.crop(data['trim']),(x0,y0))
    matrix=(1/scale,0,ax-64/scale,0,1/scale,ay-114/scale)
    return clean.transform((128,128),Image.Transform.AFFINE,matrix,Image.Resampling.BICUBIC)

def mouth_center(image,direction):
    if direction=='up':return [64,53]
    box={'down':(40,48,88,96),'left':(10,45,62,96),'right':(67,45,118,96)}[direction]
    points=set()
    for y in range(box[1],box[3]):
        for x in range(box[0],box[2]):
            r,g,b,a=image.getpixel((x,y))
            if a>128 and 45<r<205 and g<70 and b<75 and r>g*2.2:points.add((x,y))
    groups=[]
    while points:
        first=points.pop();q=deque([first]);group=[first]
        while q:
            x,y=q.popleft()
            for point in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
                if point in points:points.remove(point);q.append(point);group.append(point)
        groups.append(group)
    if not groups:return {'down':[64,75],'left':[36,72],'right':[92,72]}[direction]
    group=max(groups,key=len)
    if len(group)<12:return {'down':[64,75],'left':[36,72],'right':[92,72]}[direction]
    return [round((min(x for x,y in group)+max(x for x,y in group))/2),round((min(y for x,y in group)+max(y for x,y in group))/2)]

packed={};catalog={'schema':'element-eater.elemental-heroes.v1','frameSize':128,'pivot':[64,114],'elementCount':5,'sheetCount':20,'frameCount':640,'elements':{}}
checks=[]
for element,name in ELEMENTS.items():
    rows_by_state={state:read_source(SOURCE/element/f'{state}-generated.png') for state in STATES}
    first=rows_by_state['idle'][0][0]
    target=neutral.crop((0,0,128,128)).getchannel('A').point(lambda v:255 if v>=128 else 0).getbbox()
    scale=(target[2]-target[0])/(first['body'][2]-first['body'][0])
    for rows in rows_by_state.values():
        for row in rows:
            for pose in row:
                ax,ay=pose['anchor'];x0,y0,x1,y1=pose['trim']
                for room,extent in [(61,ax-x0),(61,x1-ax),(110,ay-y0),(11,y1-ay)]:
                    if extent>0:scale=min(scale,room/extent)
    assert .2<scale<1.2,(element,'unexpected packing scale',scale)
    scale=round(scale*.998,7)
    element_frames={state:[[pack_pose(pose,scale) for pose in row] for row in rows] for state,rows in rows_by_state.items()}
    for row in range(4):
        base=element_frames['idle'][row][0]
        for state in ['idle','attack','ingest']:
            for pose in element_frames[state][row]:pose.paste(base.crop((0,108,128,128)),(0,108))
        for state in ['attack','ingest']:
            element_frames[state][row][0]=base.copy();element_frames[state][row][7]=base.copy()
    packed[element]=element_frames
    element_folder=ASSETS/element;element_folder.mkdir(exist_ok=True)
    entry={'name':name,'scale':scale,'states':{},'mouths':{},'ingestMouths':{}}
    for row,direction in enumerate(DIRS):
        entry['mouths'][direction]=mouth_center(element_frames['attack'][row][3],direction)
        entry['ingestMouths'][direction]=mouth_center(element_frames['ingest'][row][3],direction)
    for state,(state_name,fps,loop) in STATES.items():
        sheet=Image.new('RGBA',(1024,512));frame_map={};animations={}
        for row,direction in enumerate(DIRS):
            for col,image in enumerate(element_frames[state][row]):
                assert image.getbbox(),(element,state,direction,col,'blank')
                bounds=image.getchannel('A').point(lambda v:255 if v>=96 else 0).getbbox()
                assert bounds[0]>=1 and bounds[1]>=1 and bounds[2]<=127 and bounds[3]<=127,(element,state,direction,col,'clipped',bounds)
                if state!='walk':assert image.crop((0,108,128,128)).tobytes()==element_frames['idle'][row][0].crop((0,108,128,128)).tobytes()
                sheet.paste(image,(col*128,row*128))
                frame_map[f'{direction}_{col}']={'frame':{'x':col*128,'y':row*128,'w':128,'h':128},'duration':1000/fps,'pivotPixelsTopLeft':{'x':64,'y':114},'pico2dClip':{'left':col*128,'bottom':(3-row)*128,'width':128,'height':128}}
            unique=len({pose.tobytes() for pose in element_frames[state][row]})
            assert unique>=3,(element,state,direction,'not animated')
            animations[f'{state}_{direction}']={'frames':[f'{direction}_{col}' for col in range(8)],'fps':fps,'loop':loop}
            if not loop:animations[f'{state}_{direction}'].update(next='idle',events=[{'frame':3 if state=='attack' else 4,'name':'spawn_basic_projectile' if state=='attack' else 'consume_orb','once':True}])
            checks.append({'element':element,'state':state,'direction':direction,'uniqueFrames':unique,'fixedFeet':state!='walk'})
        image_name=f'hero-{element}-{state}.png';sheet.save(element_folder/image_name)
        metadata={'schema':'element-eater.sprite-atlas.v1','image':image_name,'imageSize':{'width':1024,'height':512},'state':element,'animationState':state,'layout':{'rows':DIRS,'columns':8},'frameSize':{'width':128,'height':128},'pivotPixelsTopLeft':{'x':64,'y':114},'recommendedDrawScale':.5,'frames':frame_map,'animations':animations,'source':f'../elemental-source-v1/{element}/{state}-generated.png','uniformSourceScale':scale,'sha256':hashlib.sha256((element_folder/image_name).read_bytes()).hexdigest(),'note':'원소별 캐릭터 애니메이션 에셋. Space 기본 공격과 R 고유 능력은 별도이며 본게임 미연결.'}
        if state=='attack':metadata.update(timing={'releaseFrame':3,'releaseTime':.25,'status':'initial-animation-proposal'},muzzlePixelsTopLeft={direction:dict(zip(['x','y'],entry['mouths'][direction])) for direction in DIRS},drawProjectileBehindHero=['up'])
        if state=='ingest':metadata.update(timing={'consumeFrame':4,'consumeTime':4/12,'status':'initial-animation-proposal'},mouthPixelsTopLeft={direction:dict(zip(['x','y'],entry['ingestMouths'][direction])) for direction in DIRS},orbIsSeparate=True,drawOrbBehindHero=['up'])
        (element_folder/f'hero-{element}-{state}.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
        entry['states'][state]={'image':f'{element}/'+image_name,'fps':fps,'loop':loop,'label':state_name}
    catalog['elements'][element]=entry
    print(f'Packed {element}: four sheets, 128 frames, scale {scale}',flush=True)

(OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
if args.report:args.report.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
orbs={}
for element in ELEMENTS:
    image=Image.open(PROJECT/f'assets/items/elements/break-release-v3/sprites/{element}-orb.png').convert('RGBA');image.save(OUT/f'orbs/{element}-orb.png');orbs[element]=image

def pose_at(element,state,direction,t):
    row=DIRS.index(direction)
    if STATES[state][2]:return packed[element][state][row][int(t*STATES[state][1]+1e-6)%8],None
    phase=t%2
    if phase<.4 or phase>=.4+8/12:return packed[element]['idle'][row][0],None
    elapsed=phase-.4
    return packed[element][state][row][min(7,int(elapsed*12+1e-6))],elapsed

def scene(element,state,direction,t,scale=1.25):
    canvas=Image.new('RGBA',(180,183));sprite,elapsed=pose_at(element,state,direction,t);origin=(10,7);art=sprite.resize((160,160),Image.Resampling.LANCZOS)
    def paint_object():
        if state=='attack' and elapsed is not None and elapsed>=.25:
            mx,my=catalog['elements'][element]['mouths'][direction];dx,dy={'down':(0,1),'left':(-1,0),'right':(1,0),'up':(0,-1)}[direction]
            distance=min(58,(elapsed-.25)*160);x,y=mx+dx*distance,my+dy*distance;size=10
        elif state=='ingest' and (t%2)<.4+4/12:
            pull_elapsed=max(0,t%2-.4);start={'down':(64,125),'left':(12,74),'right':(116,74),'up':(64,6)}[direction];goal=catalog['elements'][element]['ingestMouths'][direction]
            p=max(0,min(1,(pull_elapsed-1/12)/(2/12)));ease=p*p*(3-2*p);x,y=start[0]+(goal[0]-start[0])*ease,start[1]+(goal[1]-start[1])*ease;size=21*(1-p*.9)
        else:return
        n=max(1,round(size*scale));item=orbs[element].resize((n,n),Image.Resampling.LANCZOS);canvas.alpha_composite(item,(round(origin[0]+x*scale-n/2),round(origin[1]+y*scale-n/2)))
    if direction=='up':paint_object()
    canvas.alpha_composite(art,origin)
    if direction!='up':paint_object()
    return canvas

def overview(t,element=None):
    rows=list(ELEMENTS) if element is None else DIRS
    image=Image.new('RGB',(878,86+len(rows)*187),'#14261e');draw=ImageDraw.Draw(image)
    title='원소별 캐릭터 · 대기 / 걷기 / 기본 공격 / 구슬 먹기' if element is None else f'{ELEMENTS[element]} 캐릭터 · 4방향 × 4동작'
    draw.text((18,12),title,font=FONT(22),fill='#f5edd4')
    for col,(state,(label,_,_)) in enumerate(STATES.items()):draw.text((100+col*193,54),label,font=FONT(18),fill='#c6d7ab')
    for row,key in enumerate(rows):
        el=key if element is None else element;direction='down' if element is None else key;y=83+row*187
        draw.text((8,y+70),ELEMENTS[el] if element is None else DIR_NAMES[row],font=FONT(17),fill='#e7dfbd')
        for col,state in enumerate(STATES):
            x=83+col*193;draw.rounded_rectangle((x,y,x+180,y+178),radius=12,fill='#233e30',outline='#4d6547')
            art=scene(el,state,direction,t);image.paste(art,(x,y),art)
    return image

for element in [None,*ELEMENTS]:
    images=[overview(index/20,element) for index in range(80)]
    filename='all-elements-front.gif' if element is None else f'previews/{element}-four-states.gif'
    images[0].save(OUT/filename,save_all=True,append_images=images[1:],duration=50,loop=0,disposal=2,optimize=True)
    if element is None:overview(.65).save(OUT/'preview-still.png')
    print(f'Rendered {filename}',flush=True)

template=TEMPLATE.read_text(encoding='utf-8').replace('/* CATALOG */',json.dumps(catalog,ensure_ascii=False)).replace('/* ASSET_BASE */',json.dumps(os.path.relpath(ASSETS,OUT).replace('\\','/')))
(OUT/'preview.html').write_text(template,encoding='utf-8')
print('COMPLETE: 20 sheets / 640 frames, PNG + JSON + GIF + HTML.',flush=True)
