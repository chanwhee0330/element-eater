"""image_gen 원화를 자르고 정렬해 PNG/JSON·미리보기를 만든다. 원화의 도형·색은 그리지 않는다."""
from pathlib import Path
from statistics import median
import argparse, base64, hashlib, json, math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/sprites/hero/neutral'
SOURCE = ASSETS / 'source/raster'
CFG = json.loads((SOURCE / 'manifest.json').read_text(encoding='utf-8'))
DIRECTIONS = CFG['directions']
S = CFG['frameSize']
PX, PY = CFG['pivot']
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, default=ASSETS)
parser.add_argument('--preview-dir', type=Path, default=ROOT / 'outputs/previews/hero-neutral')
parser.add_argument('--before-dir', type=Path)
parser.add_argument('--rear-before-dir', type=Path, help='뒷모습 걷기 수정 전 PNG 폴더')
args = parser.parse_args()
OUT, PREVIEW = args.output_dir.resolve(), args.preview_dir.resolve()
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
fonts = Path('C:/Windows/Fonts/malgun.ttf')
def font(size):
    return ImageFont.truetype(str(fonts), size) if fonts.exists() else ImageFont.load_default(size=size)

def source_cells(file, columns=8, rows=4, trim_margin=None):
    im = Image.open(file).convert('RGBA')
    items = []
    for row in range(rows):
        frames = []
        for col in range(columns):
            # Generated canvases need not divide evenly by 8/4: keep exact integer boundaries.
            box = (round(col*im.width/columns), round(row*im.height/rows),
                   round((col+1)*im.width/columns), round((row+1)*im.height/rows))
            cell = im.crop(box)
            a = cell.getchannel('A')
            visible = a.getbbox()
            # A threshold is used only for measuring the body/feet, never to alter asset alpha.
            solid = a.point(lambda x: 255 if x >= 96 else 0)
            body = solid.getbbox()
            assert visible and body, (file, row, col)
            if trim_margin is not None:
                # Crop distant low-alpha generation dust; keep raw RGBA inside the padded pose.
                visible = (max(0, body[0]-trim_margin), max(0, body[1]-trim_margin),
                           min(cell.width, body[2]+trim_margin), min(cell.height, body[3]+trim_margin))
            h = body[3]-body[1]
            centers = []
            for y in range(round(body[1]+h*.42), round(body[1]+h*.82)):
                xs = [x for x in range(cell.width) if solid.getpixel((x,y))]
                if xs: centers.append(sum(xs)/len(xs))
            anchor = (median(centers), body[3])
            frames.append(dict(cell=cell, visible=visible, anchor=anchor, sourceRect=box,
                               sourceState=file.stem.removesuffix('-source'), sourceFrame=col,
                               sourceImage=file.name, sourceRow=row))
        items.append(frames)
    return items

raw = {state: source_cells(SOURCE / cfg['source']) for state,cfg in CFG['states'].items()}
scale = CFG['sourceScale']
for rows in raw.values():
    for row in rows:
        for item in row:
            x0,y0,x1,y1 = item['visible']; ax,ay = item['anchor']
            for available, extent in [(PX-3,ax-x0),(S-PX-3,x1-ax),(PY-3,ay-y0),(S-PY-3,y1-ay)]:
                if extent>0: scale = min(scale,available/extent)
scale = round(scale*.998,6)

# Separate rear art replaces only the requested facing. Existing front/side pixels and scale stay intact.
overrides = {}
for direction, override in CFG.get('directionOverrides', {}).items():
    source = source_cells(SOURCE / override['source'], columns=8, rows=len(override['rows']),
                          trim_margin=override.get('trimMargin'))
    override_scale = override['sourceScale']
    for row in source:
        for item in row:
            x0,y0,x1,y1 = item['visible']; ax,ay = item['anchor']
            for available, extent in [(PX-3,ax-x0),(S-PX-3,x1-ax),(PY-3,ay-y0),(S-PY-3,y1-ay)]:
                if extent>0: override_scale = min(override_scale,available/extent)
    override_scale = round(override_scale*.998,6)
    for state, row in zip(override['rows'], source):
        for item in row: item['sourceState'] = state
        raw[state][DIRECTIONS.index(direction)] = row
        overrides[state,direction] = override_scale

packed, atlases = {}, {}
for state,cfg in CFG['states'].items():
    rows = []
    for direction, row in zip(DIRECTIONS, raw[state]):
        pose_scale = overrides.get((state,direction), scale)
        frames = []
        for item in row:
            box=item['visible']; ax,ay=item['anchor']
            trimmed=item['cell'].crop(box)
            resized=trimmed.resize((max(1,round(trimmed.width*pose_scale)),max(1,round(trimmed.height*pose_scale))),Image.Resampling.LANCZOS)
            at=(round(PX-(ax-box[0])*pose_scale),round(PY-(ay-box[1])*pose_scale))
            assert at[0]>=0 and at[1]>=0 and at[0]+resized.width<=S and at[1]+resized.height<=S, (state,item['sourceFrame'],at)
            image=Image.new('RGBA',(S,S))
            # Raw RGBA copy, not alpha-masked paste: retain the generated soft edges exactly once.
            image.paste(resized,at)
            frames.append(image)
        rows.append(frames)
    packed[state]=rows

# Identical ready/return poses make attack transitions connect to the new idle design.
for row in range(4):
    packed['attack'][row][0]=packed['idle'][row][0].copy()
    packed['attack'][row][7]=packed['idle'][row][0].copy()

for state,cfg in CFG['states'].items():
    sheet=Image.new('RGBA',(S*8,S*4));frames={};animations={}
    for row,direction in enumerate(DIRECTIONS):
        for i,image in enumerate(packed[state][row]):
            sheet.paste(image,(i*S,row*S))
            bounds=image.getbbox(); assert bounds
            assert bounds[0]>0 and bounds[1]>0 and bounds[2]<S and bounds[3]<S, (state,direction,i,bounds)
            source=raw['idle' if state=='attack' and i in (0,7) else state][row][0 if state=='attack' and i in (0,7) else i]
            frames[f'{direction}_{i}']={
                'frame':{'x':i*S,'y':row*S,'w':S,'h':S},
                'pivotPixelsTopLeft':{'x':PX,'y':PY},
                'opaqueBoundsInCell':dict(zip(['x0','y0','x1','y1'],[bounds[0],bounds[1],bounds[2]-1,bounds[3]-1])),
                'pico2dClip':{'left':i*S,'bottom':(3-row)*S,'width':S,'height':S},
                'sourcePose':{'state':source['sourceState'],'frame':source['sourceFrame'],
                              'image':f'source/raster/{source["sourceImage"]}', 'row':source['sourceRow']},
            }
        animations[f'{state}_{direction}']={'frames':[f'{direction}_{i}' for i in range(8)],'fps':cfg['fps'],'loop':cfg['loop']}
    name=f'hero-neutral-{state}'
    file=OUT/f'{name}.png'; sheet.save(file)
    atlas={'schema':'element-eater.sprite-atlas.v1','image':file.name,'imageSize':{'width':sheet.width,'height':sheet.height},
           'state':'neutral','animationState':state,'layout':{'rows':DIRECTIONS,'columns':8},'frameSize':{'width':S,'height':S},
           'coordinateSystem':'frame and pivot use image top-left origin; pico2dClip uses bottom-left origin',
           'recommendedDrawScale':CFG['recommendedDrawScale'],'frames':frames,'animations':animations,
           'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
           'generator':{'tool':'image_gen + RGBA atlas packing','source':f'source/raster/{cfg["source"]}',
                        'directionOverrides':{direction:{'source':f'source/raster/{override["source"]}',
                                                        'uniformSourceScale':overrides[state,direction]}
                                              for direction,override in CFG.get('directionOverrides',{}).items()},
                        'recipe':'source/raster/manifest.json','uniformSourceScale':scale,'command':'python tools/build_hero_sprites.py'}}
    if state=='attack':
        atlas.update(timing=CFG['attackTiming'],muzzlePixelsTopLeft=CFG['muzzlePixelsTopLeft'],drawProjectileBehindHero=['up'],
                     **CFG['neutralCombat'],
                     note='Space 무속성 기본 공격은 적 원소와 관계없이 낮은 피해·약한 넉백. 피해 수치와 넉백 거리는 시험값. 공격은 한 번 재생 후 idle, 실제 게임 판정 미구현.')
    (OUT/f'{name}.json').write_text(json.dumps(atlas,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    atlases[state]=atlas
    print(f'{name}: {sheet.width}x{sheet.height}, 32 frames, RGBA, pivot {PX},{PY}, scale {scale}')

def paste_scaled(dest,image,x,y,width):
    height=round(image.height*width/image.width)
    sprite=image.resize((width,height),Image.Resampling.LANCZOS)
    dest.paste(sprite,(round(x),round(y)),sprite)

def contact(states,path):
    cw,pad,left,head=128,12,94,66
    board=Image.new('RGB',(left+8*(cw+pad),head+len(states)*4*158+12),'#152125')
    d=ImageDraw.Draw(board)
    d.text((18,12),'엘리먼트 이터 · 둥근 무속성 주인공',font=font(22),fill='#f2efd7')
    d.text((18,40),'아이보리 몸 · 큰 표정 · 둥근 손발 · 초록 잎 귀',font=font(12),fill='#b0c4ae')
    for sr,state in enumerate(states):
        for row,direction in enumerate(DIRECTIONS):
            y=head+(sr*4+row)*158
            d.text((8,y+46),state,font=font(12),fill='#d7dfc3')
            d.text((8,y+64),direction,font=font(12),fill='#9fbaaa')
            for i,image in enumerate(packed[state][row]):
                x=left+i*(cw+pad)
                d.rounded_rectangle((x,y,x+cw-1,y+cw-1),radius=8,fill='#233231')
                board.paste(image,(x,y),image)
                d.text((x+4,y+130),str(i)+(' 발사' if state=='attack' and i==3 else ''),font=font(11),fill='#9fbaaa')
    board.save(path)

contact(['idle','walk'],PREVIEW/'hero-neutral-contact.png')
contact(['attack'],PREVIEW/'hero-neutral-attack-contact.png')

# Compact live-motion preview, with true source FPS sampled on a 20 FPS timeline.
W,H=760,842
base=Image.new('RGB',(W,H),'#152125');d=ImageDraw.Draw(base)
d.text((24,18),'엘리먼트 이터 · 새로운 무속성 주인공',font=font(24),fill='#f2efd7')
d.text((24,57),'원소 컨셉과 맞춘 통통한 체형과 부드러운 표정',font=font(14),fill='#b0c4ae')
labels=['아래 · 정면','왼쪽','오른쪽','위 · 뒷면']
for sr,state in enumerate(['idle','walk','attack']):
    y=102+sr*234
    title={'idle':'대기 · 숨쉬기와 잎 흔들림','walk':'걷기 · 발 교차와 몸 반동','attack':'공격 · 준비, 발사, 복귀'}[state]
    d.text((24,y),title,font=font(15),fill='#dae5c5')
    for col,label in enumerate(labels):
        x=24+col*182
        d.rounded_rectangle((x,y+29,x+165,y+215),radius=10,fill='#233231')
        d.text((x+83,y+190),label,anchor='mt',font=font(12),fill='#b0c4ae')
d.text((24,817),'4방향 · 동작마다 8프레임 · 투명 PNG 원본 별도',font=font(11),fill='#9fbaaa')
gif_frames=[]
for tick in range(80):
    t=tick/20;image=base.copy()
    for sr,state in enumerate(['idle','walk','attack']):
        cfg=CFG['states'][state];age=t%2 if state=='attack' else t
        frame=min(7,int(age*cfg['fps'])) if state=='attack' else int(age*cfg['fps'])%8
        for col in range(4):
            sprite=packed[state][col][frame]
            paste_scaled(image,sprite,24+col*182+3,102+sr*234+30,160)
    gif_frames.append(image)
palette=gif_frames[7].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
gif=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in gif_frames]
gif[0].save(PREVIEW/'hero-neutral-preview.gif',save_all=True,append_images=gif[1:],duration=50,loop=0,disposal=2,optimize=False)

encoded={state:base64.b64encode((OUT/f'hero-neutral-{state}.png').read_bytes()).decode() for state in CFG['states']}
data=json.dumps({'images':encoded,'size':S,'states':CFG['states'],'pivot':[PX,PY]},ensure_ascii=False)
html='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>엘리먼트 이터 · 주인공 미리보기</title><style>
body{background:#152125;color:#f2efd7;font:16px system-ui;margin:0}main{max-width:950px;margin:36px auto;padding:0 24px}h1{font-size:26px}p{color:#b0c4ae;line-height:1.6}h2{font-size:18px;margin-top:28px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.card{background:#233231;border-radius:12px;text-align:center;padding:12px 4px}.card canvas{width:180px;height:180px;max-width:100%;object-fit:contain}.card div{font-size:14px;color:#b0c4ae}.controls{display:flex;gap:14px;align-items:center;flex-wrap:wrap}button,select{color:#f2efd7;background:#344a40;border:1px solid #6b826b;border-radius:6px;padding:8px;font:inherit}@media(max-width:620px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style><main><h1>엘리먼트 이터 · 무속성 주인공</h1><p>둥근 아이보리 몸, 초록 잎 귀와 큰 표정<br>대기 · 걷기 · 공격 애니메이션 미리보기</p><div class="controls"><button id="play">일시정지</button><label>속도 <select id="speed"><option value="0.5">0.5배</option><option value="1" selected>1배</option><option value="2">2배</option></select></label><label><input id="pivot" type="checkbox"> 발밑 기준점</label></div><div id="gallery"></div><p>공격은 실제 사용 시 한 번 재생합니다. 이 미리보기에서는 2초마다 반복합니다.</p></main><script>
const data=DATA;const dirs=['아래 · 정면','왼쪽','오른쪽','위 · 뒷면'];const views=[];let t=0,last=performance.now(),playing=true;
for(const state of ['idle','walk','attack']){const h=document.createElement('h2');h.textContent={idle:'대기',walk:'걷기',attack:'공격'}[state];const grid=document.createElement('div');grid.className='grid';document.querySelector('#gallery').append(h,grid);const img=new Image();img.src='data:image/png;base64,'+data.images[state];for(let row=0;row<4;row++){const card=document.createElement('div'),canvas=document.createElement('canvas'),label=document.createElement('div');card.className='card';canvas.width=canvas.height=data.size;label.textContent=dirs[row];card.append(canvas,label);grid.append(card);views.push({state,row,img,canvas});}}
document.querySelector('#play').onclick=()=>{playing=!playing;document.querySelector('#play').textContent=playing?'일시정지':'재생';};
function draw(now){if(playing)t+=(now-last)/1000*Number(document.querySelector('#speed').value);last=now;for(const v of views){const cfg=data.states[v.state],age=v.state==='attack'?t%2:t,index=v.state==='attack'?Math.min(7,Math.floor(age*cfg.fps)):Math.floor(age*cfg.fps)%8,ctx=v.canvas.getContext('2d'),s=data.size;ctx.clearRect(0,0,s,s);if(v.img.complete&&v.img.naturalWidth)ctx.drawImage(v.img,index*s,v.row*s,s,s,0,0,s,s);if(document.querySelector('#pivot').checked){ctx.fillStyle='#eea778';ctx.fillRect(data.pivot[0]-4,data.pivot[1],9,1);ctx.fillRect(data.pivot[0],data.pivot[1]-4,1,9);}}requestAnimationFrame(draw);}requestAnimationFrame(draw);
</script></html>'''.replace('DATA',data)
(PREVIEW/'hero-neutral-preview.html').write_text(html,encoding='utf-8')

if args.before_dir:
    before=Image.open(args.before_dir/'hero-neutral-idle.png').convert('RGBA')
    comparison=Image.new('RGB',(680,760),'#152125');d=ImageDraw.Draw(comparison)
    d.text((26,18),'무속성 주인공 · 둥근 체형 재제작',font=font(24),fill='#f2efd7')
    d.text((26,58),'더 큰 표정 · 말랑한 몸통 · 자연스럽게 이어진 손발',font=font(13),fill='#b0c4ae')
    for col,title in enumerate(['이전','새 디자인']):d.text((180+320*col,103),title,anchor='mt',font=font(18),fill='#dae5c5')
    for row,(direction,label) in enumerate([('down','정면'),('right','옆모습')]):
        y=154+row*282;d.text((30,y-26),label,font=font(14),fill='#b0c4ae')
        r=DIRECTIONS.index(direction)
        old=before.crop((0,r*64,64,(r+1)*64)).resize((256,256),Image.Resampling.NEAREST)
        new=packed['idle'][r][0].resize((256,256),Image.Resampling.LANCZOS)
        for col,sprite in enumerate([old,new]):
            x=30+col*320;d.rounded_rectangle((x,y,x+279,y+261),radius=12,fill='#233231');comparison.paste(sprite,(x+12,y),sprite)
    d.text((26,735),'대기·걷기·공격 모두 같은 체형과 표정으로 교체',font=font(12),fill='#9fbaaa')
    comparison.save(PREVIEW/'hero-neutral-round-before-after.png')
print('Atlas PNG/JSON, GIF, offline HTML and contact previews saved')

if args.rear_before_dir:
    before=Image.open(args.rear_before_dir/'hero-neutral-walk.png').convert('RGBA')
    row=DIRECTIONS.index('up')
    old_size=before.height//4
    old=[before.crop((i*old_size,row*old_size,(i+1)*old_size,(row+1)*old_size)) for i in range(8)]
    new=packed['walk'][row]
    board=Image.new('RGB',(1220,410),'#152125');d=ImageDraw.Draw(board)
    d.text((24,15),'무속성 주인공 · 뒷모습 걷기 수정',font=font(23),fill='#f2efd7')
    d.text((24,52),'팔은 몸 앞에 가려지고, 뒤꿈치는 좌우로 교차 · 잎 뒷면과 등 명암',font=font(14),fill='#b0c4ae')
    for r,(label,frames) in enumerate([('수정 전',old),('수정 후',new)]):
        y=95+r*150;d.text((10,y+48),label,font=font(14),fill='#dae5c5')
        for i,sprite in enumerate(frames):
            x=94+i*140;d.rounded_rectangle((x,y,x+127,y+127),radius=8,fill='#233231')
            paste_scaled(board,sprite,x,y,128)
            d.text((x+5,y+130),str(i),font=font(11),fill='#9fbaaa')
    board.save(PREVIEW/'hero-neutral-rear-before-after.png')
    base=Image.new('RGB',(700,368),'#152125');d=ImageDraw.Draw(base)
    d.text((24,14),'무속성 · 화면 위쪽으로 걸어가는 뒷모습',font=font(21),fill='#f2efd7')
    for col,label in enumerate(['수정 전','수정 후']):
        x=20+col*350;d.rounded_rectangle((x,62,x+309,329),radius=12,fill='#233231')
        d.text((x+155,337),label,anchor='mt',font=font(14),fill='#b0c4ae')
    motion=[]
    for i in range(8):
        frame=base.copy()
        for col,sprite in enumerate([old[i],new[i]]):paste_scaled(frame,sprite,47+col*350,66,256)
        motion.append(frame)
    palette=motion[0].quantize(colors=256,method=Image.Quantize.MEDIANCUT)
    motion=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in motion]
    motion[0].save(PREVIEW/'hero-neutral-rear-before-after.gif',save_all=True,
                   append_images=motion[1:],duration=100,loop=0,disposal=2,optimize=False)
    print('Rear-view before/after contact and 10fps motion preview saved')
