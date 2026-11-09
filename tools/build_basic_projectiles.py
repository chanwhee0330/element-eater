"""이미지 생성 원화 6종을 4방향 비행 시트와 독립 HTML/GIF로 만듭니다."""
from pathlib import Path
import base64
import hashlib
import json
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/effects/basic-projectiles/v1'
OUT=ROOT/'outputs/previews/basic-projectiles'
ELEMENTS={'neutral':('무속성','아이보리 충격탄','부드러운 압축탄과 크림색 바람 꼬리'),
          'water':('물','물방울탄','푸른 물방울과 흐르는 물결 꼬리'),
          'fire':('불','불꽃탄','뜨거운 불씨와 일렁이는 주황 불꽃'),
          'wind':('바람','회오리탄','연두색 압축 공기와 소용돌이'),
          'earth':('흙','돌조각탄','각진 황갈색 돌과 먼지·작은 파편'),
          'lightning':('번개','전기탄','노란 지그재그와 보랏빛 전기 가지')}
DIRS=['down','left','right','up']
SIZE=160
PIVOT=(80,80)
FPS=12


def data_uri(path,mime='image/png'):
    return 'data:'+mime+';base64,'+base64.b64encode(Path(path).read_bytes()).decode('ascii')


def measure_head(image,element):
    """꼬리의 최대 범위가 아니라 오른쪽 불투명 본체를 기준으로 등록합니다."""
    a=np.asarray(image.getchannel('A'))
    front=.69 if element in ['wind','fire'] else .53
    y,x=np.nonzero((a>=220)&(np.indices(a.shape)[1]>=image.width*front))
    top,bottom=int(y.min()),int(y.max())+1
    right=int(x.max())+1
    height=bottom-top
    return (right-height*.5,(top+bottom)/2),height


def pack():
    ASSETS.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    inputs={}
    for element in ELEMENTS:
        source=Image.open(ASSETS/f'source/{element}-flight-source.png').convert('RGBA')
        frames=[];centers=[];heights=[]
        for i in range(8):
            row,col=divmod(i,4)
            tile=source.crop((round(col*source.width/4),round(row*source.height/2),
                              round((col+1)*source.width/4),round((row+1)*source.height/2)))
            center,height=measure_head(tile,element);frames.append(tile);centers.append(center);heights.append(height)
        scale=32/float(np.median(heights));fit=1.
        for tile,(cx,cy) in zip(frames,centers):
            bounds=tile.getchannel('A').point(lambda a:255 if a>=8 else 0).getbbox()
            for extent in [cx-bounds[0],bounds[2]-cx,cy-bounds[1],bounds[3]-cy]:
                if extent>0:fit=min(fit,75/(extent*scale))
        inputs[element]=(frames,centers,scale*fit*.98)
    catalog={'schema':'element-eater.basic-projectiles.v1','frameSize':SIZE,'pivot':list(PIVOT),
             'directions':DIRS,'fps':FPS,'frameCount':8,'drawRatioToHero':.5,
             'note':'Space 기본 공격 비행 연출 시안. 수치·발사 시점은 초기안. R 스킬 및 본게임 전투와 별도.',
             'elements':{}}
    for element,(frames,centers,scale) in inputs.items():
        packed=[]
        for tile,(cx,cy) in zip(frames,centers):
            packed.append(tile.transform((SIZE,SIZE),Image.Transform.AFFINE,
                (1/scale,0,cx-80/scale,0,1/scale,cy-80/scale),Image.Resampling.BICUBIC))
        sheet=Image.new('RGBA',(SIZE*8,SIZE*4));frames_meta={}
        for row,direction in enumerate(DIRS):
            for col,tile in enumerate(packed):
                frame={'right':tile,'down':tile.transpose(Image.Transpose.ROTATE_270),
                       'left':tile.transpose(Image.Transpose.ROTATE_180),
                       'up':tile.transpose(Image.Transpose.ROTATE_90)}[direction]
                sheet.paste(frame,(col*SIZE,row*SIZE))
                frames_meta[f'{direction}_{col}']={'frame':{'x':col*SIZE,'y':row*SIZE,'w':SIZE,'h':SIZE},
                    'duration':1000/FPS,'pivotPixelsTopLeft':{'x':80,'y':80},
                    'pico2dClip':{'left':col*SIZE,'bottom':(3-row)*SIZE,'width':SIZE,'height':SIZE}}
        filename=f'{element}-flight.png';sheet.save(ASSETS/filename)
        meta={'schema':'element-eater.sprite-atlas.v1','image':filename,'imageSize':{'width':SIZE*8,'height':SIZE*4},
              'frameSize':{'width':SIZE,'height':SIZE},'layout':{'rows':DIRS,'columns':8},
              'element':element,'animationState':'basic-projectile-flight','fps':FPS,'loop':True,
              'pivotPixelsTopLeft':{'x':80,'y':80},'recommendedDrawScale':.25,
              'registration':{'method':'opaque-leading-core','scaleAcrossFrames':scale,
                              'sourceCenters':centers,'animatedTailNeverDefinesCenter':True},
              'timing':{'spawnAttackFrame':3,'spawnTimeSeconds':.25,'status':'initial-animation-proposal'},
              'combatImplemented':False,'frames':frames_meta,
              'sha256':hashlib.sha256((ASSETS/filename).read_bytes()).hexdigest(),
              'generator':{'command':'python tools/build_basic_projectiles.py','source':f'source/{element}-flight-source.png'}}
        (ASSETS/f'{element}-flight.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        label,title,description=ELEMENTS[element]
        catalog['elements'][element]={'name':label,'title':title,'description':description,'image':filename}
    (ASSETS/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    validate(catalog)
    return catalog


def validate(catalog):
    for element,entry in catalog['elements'].items():
        path=ASSETS/entry['image'];sheet=Image.open(path).convert('RGBA')
        meta=json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256']
        assert len(meta['frames'])==32
        for row in range(4):
            frames=[sheet.crop((i*SIZE,row*SIZE,(i+1)*SIZE,(row+1)*SIZE)) for i in range(8)]
            assert len({f.tobytes() for f in frames})==8,(element,row,'static animation')
            for frame in frames:
                alpha=frame.getchannel('A');lo,hi=alpha.getextrema();assert lo==0 and hi>=240
                bounds=alpha.point(lambda a:255 if a>=8 else 0).getbbox()
                assert bounds[0]>0 and bounds[1]>0 and bounds[2]<SIZE and bounds[3]<SIZE,(element,row,bounds)
        for i in range(8):
            right=sheet.crop((i*SIZE,2*SIZE,(i+1)*SIZE,3*SIZE))
            assert right.transpose(Image.Transpose.ROTATE_270).tobytes()==sheet.crop((i*SIZE,0,(i+1)*SIZE,SIZE)).tobytes()
        nose=[]
        for i in range(8):
            a=np.asarray(sheet.crop((i*SIZE,2*SIZE,(i+1)*SIZE,3*SIZE)).getchannel('A'))
            y,x=np.nonzero(a>=220);tip=int(x.max())
            y,x=np.nonzero((a>=220)&(np.indices(a.shape)[1]>=tip-5))
            nose.append((tip,(float(y.min())+float(y.max()))/2))
        assert np.ptp([n[0] for n in nose])<=2,(element,'leading core size drift',nose)
        assert np.ptp([n[1] for n in nose])<=1.5,(element,'leading core center drift',nose)
    print('Validated six transparent atlases / 192 moving directional frames.',flush=True)


def preview_data(catalog):
    hero=json.loads((ROOT/'outputs/previews/hero-elements/catalog.json').read_text(encoding='utf-8'))
    data={'projectiles':catalog,'heroes':hero['elements'],'images':{}}
    for element,entry in catalog['elements'].items():
        data['images'][f'projectile/{element}']=data_uri(ASSETS/entry['image'])
        for state in ['idle','attack']:
            data['images'][f'hero/{element}/{state}']=data_uri(ROOT/'assets/sprites/hero'/hero['elements'][element]['states'][state]['image'])
    return data


def render(catalog):
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',size)
    sheets={el:Image.open(ASSETS/e['image']).convert('RGBA') for el,e in catalog['elements'].items()}
    frames=[]
    for tick in range(32):
        board=Image.new('RGB',(960,720),'#14261e');draw=ImageDraw.Draw(board)
        draw.text((24,14),'원소별 기본 공격 투사체 · 비행 루프',font=font(25),fill='#f4edd5')
        for i,(el,entry) in enumerate(catalog['elements'].items()):
            row,col=divmod(i,3);x=20+col*315;y=66+row*320
            draw.rounded_rectangle((x,y,x+300,y+300),radius=16,fill='#233e30',outline='#4d6547')
            draw.text((x+16,y+12),entry['name']+' · '+entry['title'],font=font(19),fill='#e9e6ca')
            frame=int(tick/16*FPS)%8
            tile=sheets[el].crop((frame*SIZE,2*SIZE,(frame+1)*SIZE,3*SIZE)).resize((256,256),Image.Resampling.LANCZOS)
            board.paste(tile,(x+22,y+37),tile)
        frames.append(board)
    palette=frames[4].quantize(colors=256)
    frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    frames[0].save(OUT/'projectiles.gif',save_all=True,append_images=frames[1:],duration=[60,60,60,70]*8,loop=0,disposal=2)
    frames[0].convert('RGB').save(OUT/'preview-still.png')
    text=(ROOT/'tools/basic_projectiles_preview.html').read_text(encoding='utf-8')
    text=text.replace('/* DATA */',json.dumps(preview_data(catalog),ensure_ascii=False,separators=(',',':')))
    text=text.replace('/* FALLBACK */',data_uri(OUT/'projectiles.gif','image/gif'))
    (OUT/'preview.html').write_text(text,encoding='utf-8')


def refresh_hero_viewer():
    from render_aligned import render as render_hero
    from standalone_hero_preview import make_fallback,write_standalone
    out=ROOT/'outputs/previews/hero-elements';assets=ROOT/'assets/sprites/hero'
    catalog=json.loads((out/'catalog.json').read_text(encoding='utf-8'))
    render_hero(ROOT,out,assets)
    make_fallback(out/'all-elements-front.gif',out/'preview-fallback.gif')
    write_standalone(ROOT/'tools/hero_elements_preview.html',catalog,assets,out/'orbs',out/'preview-fallback.gif',out/'preview.html')
    shutil.copyfile(out/'preview.html',out/'standalone-preview.html')


if __name__=='__main__':
    catalog=pack();render(catalog);refresh_hero_viewer()
    from build_animation_gallery import main
    main()
