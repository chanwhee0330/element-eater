"""무속성 에셋의 연출용 GIF 조립. 게임 코드가 아니며 Pillow가 필요합니다."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/previews/neutral-attack'
HERO = ROOT / 'assets/sprites/hero/neutral'
FX = ROOT / 'assets/effects/neutral'
OUT.mkdir(parents=True, exist_ok=True)

def atlas(folder, name):
    data = json.loads((folder / f'{name}.json').read_text(encoding='utf-8'))
    return Image.open(folder / data['image']).convert('RGBA'), data

hero, hero_data = atlas(HERO, 'hero-neutral-attack')
idle, _ = atlas(HERO, 'hero-neutral-idle')
effects = {k: atlas(FX / k, f'neutral-{k}-sheet') for k in ['projectile', 'muzzle', 'impact']}

def frame(sheet, size, direction, index):
    row = ['down', 'left', 'right', 'up'].index(direction)
    return sheet.crop((index*size, row*size, (index+1)*size, (row+1)*size))

def paste_center(dest, sprite, center, scale=3, pivot=None):
    pivot = pivot or (sprite.width/2, sprite.height/2)
    im = sprite.resize((sprite.width*scale, sprite.height*scale), Image.Resampling.NEAREST)
    dest.paste(im, (round(center[0]-pivot[0]*scale), round(center[1]-pivot[1]*scale)), im)

font_path = Path('C:/Windows/Fonts/malgun.ttf')
def font(size):
    return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)

base = Image.new('RGB', (760, 598), '#131b1f')
d = ImageDraw.Draw(base)
d.text((24,18), '엘리먼트 이터 · 무속성 공격', font=font(24), fill='#f2efd7')
d.text((24,56), '피해 0 · 적 원소와 관계없이 약한 넉백', font=font(14), fill='#c2d5b2')
d.rounded_rectangle((24,94,736,358), radius=12, fill='#1d282b')
d.text((44,111), '공격 모션 + 충격탄 + 명중 효과', font=font(13), fill='#a7bdab')
d.line((52,327,708,327), fill='#3b4c46', width=1)
d.text((190,334), '주인공', anchor='mt', font=font(12), fill='#b5c8b7')
d.text((24,377), '4방향 공격 모션 · 준비 → 발사 → 복귀', font=font(14), fill='#c2d5b2')
labels = ['아래 · 정면', '왼쪽', '오른쪽', '위 · 뒷면']
for col, label in enumerate(labels):
    x = 24+182*col
    d.rounded_rectangle((x,406,x+165,575), radius=10, fill='#1d282b')
    d.text((x+83,552), label, anchor='mt', font=font(12), fill='#a7bdab')
d.text((24,584), '에셋 연출 미리보기 · 넉백 거리는 테스트용 초기값', font=font(10), fill='#8ca593')

# A simple neutral dummy exists only in this preview, not in the game's enemy asset set.
dummy = Image.new('RGBA', (30,34))
td = ImageDraw.Draw(dummy)
td.ellipse((3,2,27,29), fill='#526258')
td.ellipse((4,3,26,28), fill='#96a788')
td.ellipse((5,3,22,23), fill='#c1cbaa')
td.rectangle((9,12,10,15), fill='#35423c')
td.rectangle((19,12,20,15), fill='#35423c')
td.rectangle((12,20,17,21), fill='#6d7d63')
td.ellipse((6,27,12,32), fill='#526258')
td.ellipse((19,27,25,32), fill='#526258')

fps, total = 25, 40
hero_foot = (190,322)
release = hero_data['timing']['releaseTime']
m = hero_data['muzzlePixelsTopLeft']['right']
muzzle = (hero_foot[0]+(m['x']-32)*3, hero_foot[1]+(58-m['y'])*-3)
target = (565,271)
hit_x = target[0]-30
hit_time = release+(hit_x-muzzle[0])/(280*3)
frames = []
for tick in range(total):
    t = tick/fps
    image = base.copy(); draw = ImageDraw.Draw(image)
    attack_index = min(7, int(t*12))
    current = frame(hero,64,'right',attack_index) if t<8/12 else frame(idle,64,'right',0)
    paste_center(image,current,hero_foot,3,(32,58))
    progress = min(1,max(0,(t-hit_time)/.1))
    push = 12*3*(1-(1-progress)**3) if t>=hit_time else 0
    paste_center(image,dummy,(target[0]+push,276),3,(15,17))
    draw.text((target[0]+push,209), 'HP 100 / 100', anchor='mt', font=font(12), fill='#c2d5b2')
    draw.rectangle((target[0]-35+push,230,target[0]+35+push,235), fill='#91b16d')
    if release<=t<hit_time:
        x = muzzle[0]+(t-release)*280*3
        shot, _ = effects['projectile']
        paste_center(image,frame(shot,32,'right',int((t-release)*12)%8),(x,muzzle[1]))
    if release<=t<release+.5:
        flash, _ = effects['muzzle']
        paste_center(image,frame(flash,32,'right',min(7,int((t-release)*16))),muzzle)
    if hit_time<=t<hit_time+.5:
        impact, _ = effects['impact']
        paste_center(image,frame(impact,48,'right',min(7,int((t-hit_time)*16))),(hit_x+push,muzzle[1]))
    if t>=hit_time:
        draw.text((565,337),'피해 0 · 살짝 밀림',anchor='mt',font=font(12),fill='#e6dcc1')
    for col,direction in enumerate(['down','left','right','up']):
        spr=frame(hero,64,direction,attack_index) if t<8/12 else frame(idle,64,direction,0)
        paste_center(image,spr,(24+182*col+83,536),2,(32,58))
    frames.append(image)
palette = frames[8].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
encoded = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
encoded[0].save(OUT/'neutral-attack-preview.gif', save_all=True, append_images=encoded[1:], duration=40, loop=0, disposal=2, optimize=False)
print('neutral-attack-preview.gif: 1.6s loop, HP unchanged, 12px example knockback')
