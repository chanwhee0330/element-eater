"""최종 캐릭터 시트를 사용해 기존 내장형 미리보기도 함께 갱신합니다."""
from pathlib import Path
import base64
import json
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont


def refresh(root):
    root = Path(root)
    out = root/'outputs/previews'
    hero = root/'assets/sprites/hero/neutral'
    catalog = json.loads((out/'hero-elements/catalog.json').read_text(encoding='utf-8'))
    entry = catalog['elements']['neutral']
    sheets = {state: Image.open(hero/f'hero-neutral-{state}.png').convert('RGBA')
              for state in ('idle','walk','attack','ingest')}
    def encoded(state, uri=False):
        return ('data:image/png;base64,' if uri else '') + base64.b64encode(
            (hero/f'hero-neutral-{state}.png').read_bytes()).decode('ascii')
    for folder, name in [('hero-neutral','hero-neutral-preview.html'),('hero-neutral-ingest','preview.html')]:
        path = out/folder/name
        if not path.exists(): continue
        text = path.read_text(encoding='utf-8')
        start = text.index('const data=') + len('const data=')
        data, length = json.JSONDecoder().raw_decode(text[start:])
        if folder == 'hero-neutral':
            data['images'] = {state:encoded(state) for state in ('idle','walk','attack')}
        else:
            data.update(hero=encoded('ingest',True),idle=encoded('idle',True),mouths=entry['ingestMouths'])
        text = text[:start] + json.dumps(data,ensure_ascii=False) + text[start+length:]
        path.write_text(text,encoding='utf-8')
    # 기존 PNG 접촉표도 최종 시트에서 다시 만듭니다.
    font = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',16)
    for states, path in [(['idle','walk'],'hero-neutral/hero-neutral-contact.png'),
                         (['attack'],'hero-neutral/hero-neutral-attack-contact.png'),
                         (['ingest'],'hero-neutral-ingest/all-frames.png')]:
        board = Image.new('RGB',(1100,140*4*len(states)),'#14261e')
        draw = ImageDraw.Draw(board)
        for block,state in enumerate(states):
            for row,direction in enumerate(['정면','왼쪽','오른쪽','뒷면']):
                y=(block*4+row)*140
                draw.text((4,y+40),state+'\n'+direction,font=font,fill='#f5edd5')
                for col in range(8):
                    tile=sheets[state].crop((col*128,row*128,(col+1)*128,(row+1)*128))
                    board.paste(tile,(76+col*128,y),tile)
        board.save(out/path)
    shutil.copyfile(out/'hero-elements/previews/neutral-four-states.gif',out/'hero-neutral/hero-neutral-preview.gif')
    render_ingest(out, sheets, entry, font)
    # 오래된 빌더는 최종 PNG를 덮어쓰므로 실행하지 않습니다.
    for command in [('build_base_room.py',),('build_base_room.py','--variant','obstacles'),
                    ('render_ingame_preview.py',),('render_element_pickups.py',),
                    ('preview_neutral_attack.py',)]:
        subprocess.run([sys.executable,str(root/'tools'/command[0]),*command[1:]],cwd=root,check=True)
    projectile_catalog=root/'assets/effects/basic-projectiles/v1/catalog.json'
    if projectile_catalog.exists():
        from build_basic_projectiles import render
        render(json.loads(projectile_catalog.read_text(encoding='utf-8')))
    subprocess.run([sys.executable,str(root/'tools/build_animation_gallery.py')],cwd=root,check=True)


def render_ingest(out, sheets, entry, font):
    directions=['down','left','right','up']
    starts={'down':(64,124),'left':(9,74),'right':(119,74),'up':(64,5)}
    orbs={el:Image.open(out/f'hero-elements/orbs/{el}-orb.png').convert('RGBA')
          for el in ('water','fire','wind','earth','lightning')}
    for name,views in [('hero-neutral-ingest.gif',[(d,'water') for d in directions]),
                       ('five-elements-ingest.gif',[('down',el) for el in orbs])]:
        frames=[]
        for tick in range(40):
            t=tick/20; elapsed=t-.4; eating=0<=elapsed<8/12
            col=min(7,int(elapsed*12)) if eating else 0
            board=Image.new('RGB',(len(views)*176,218),'#14261e');draw=ImageDraw.Draw(board)
            for i,(direction,el) in enumerate(views):
                draw.text((i*176+8,6),direction+' / '+el,font=font,fill='#f5edd5')
                row=directions.index(direction)
                sprite=sheets['ingest' if eating else 'idle'].crop((col*128,row*128,(col+1)*128,(row+1)*128))
                tile=Image.new('RGBA',(128,128))
                def orb():
                    if t>=.4+4/12:return
                    p=max(0,min(1,(elapsed-1/12)/(2/12)));p=p*p*(3-2*p)
                    sx,sy=starts[direction];mx,my=entry['ingestMouths'][direction]
                    x,y=sx+(mx-sx)*p,sy+(my-sy)*p;n=max(1,round(21*(1-.9*p)))
                    tile.alpha_composite(orbs[el].resize((n,n),Image.Resampling.LANCZOS),(round(x-n/2),round(y-n/2)))
                if direction=='up':orb()
                tile.alpha_composite(sprite)
                if direction!='up':orb()
                tile=tile.resize((164,164),Image.Resampling.LANCZOS)
                board.paste(tile,(i*176+6,40),tile)
            frames.append(board)
        palette=frames[12].quantize(colors=256)
        frames=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
        frames[0].save(out/'hero-neutral-ingest'/name,save_all=True,append_images=frames[1:],duration=50,loop=0,disposal=2)


if __name__=='__main__':
    refresh(Path(__file__).resolve().parents[1])
