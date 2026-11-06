"""실제 맵·플레이어 에셋으로 일부 영역과 HUD를 조립한 인게임 구도 시안."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'assets/maps/obstacle-room'
OUT = ROOT / 'outputs/previews/obstacle-room'
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.loads((MAP / 'source/ingame-view.json').read_text(encoding='utf-8'))
data = json.loads((MAP / 'obstacle-room.json').read_text(encoding='utf-8'))
world = Image.open(MAP / data['image']).convert('RGBA')
W, H = cfg['resolution']['width'], cfg['resolution']['height']
unit = data['unitPixels']
view_w, view_h = cfg['viewUnits']['width'], cfg['viewUnits']['height']
assert abs(W / H - view_w / view_h) < 1e-9
left = max(0, min(data['columns'] - view_w, cfg['cameraCenter']['x'] - view_w / 2))
top = max(0, min(data['rows'] - view_h, cfg['cameraCenter']['y'] - view_h / 2))
crop = (round(left * unit), round(top * unit), round((left + view_w) * unit), round((top + view_h) * unit))
screen = world.crop(crop).resize((W, H), Image.Resampling.LANCZOS)
# 원소 미리보기에서도 같은 배경·카메라·HUD를 재사용한다.
background = screen.copy()
screen_unit = W / view_w
player = data['player']
position = cfg['playerCenter']
assert left < position['x'] < left + view_w and top < position['y'] < top + view_h
assert data['tiles'][int(position['y'])][int(position['x'])] in (0, 1, 2)
source_size = player['spriteFrameSize']
sheet = Image.open((MAP / player['idleImage']).resolve()).convert('RGBA')
row = ['down', 'left', 'right', 'up'].index(cfg['playerDirection'])
col = cfg['playerFrame']
sprite = sheet.crop((col * source_size, row * source_size, (col + 1) * source_size, (row + 1) * source_size))
scale = screen_unit * player['heightUnits'] / player['referenceSolidHeightPixels']
sprite = sprite.resize((round(source_size * scale), round(source_size * scale)), Image.Resampling.LANCZOS)
px, py = (position['x'] - left) * screen_unit, (position['y'] - top) * screen_unit
center = player['referenceCenterPixelsTopLeft']
at = (round(px - center['x'] * scale), round(py - center['y'] * scale))
overlay = Image.new('RGBA', (W, H))
d = ImageDraw.Draw(overlay)
foot_y = py + (player['spritePivotPixelsTopLeft']['y'] - center['y']) * scale
d.ellipse((px - 25, foot_y - 7, px + 25, foot_y + 5), fill=(26, 27, 20, 75))
screen = Image.alpha_composite(screen, overlay)
screen.alpha_composite(sprite, at)

font_path = Path('C:/Windows/Fonts/malgun.ttf')
def font(size):
    return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)

ui = Image.new('RGBA', (W, H))
d = ImageDraw.Draw(ui)
ink, muted = '#f6efd5', '#bec9af'
def panel(box, radius=12):
    d.rounded_rectangle(box, radius=radius, fill=(25, 37, 30, 232), outline=(180, 191, 149, 145), width=1)

# HUD values are a layout example, not simulated combat state.
panel((26, 24, 336, 112))
d.text((45, 37), '체력', font=font(17), fill=muted)
d.text((316, 37), f'{cfg["hudSample"]["health"]} / {cfg["hudSample"]["maxHealth"]}', font=font(17), fill=ink, anchor='rt')
d.rounded_rectangle((46, 78, 316, 92), radius=5, fill='#394638')
hp_ratio = max(0, min(1, cfg['hudSample']['health'] / cfg['hudSample']['maxHealth']))
d.rounded_rectangle((46, 78, round(46 + 270 * hp_ratio), 92), radius=5, fill='#bed879')
panel((1010, 24, 1254, 104))
d.text((1031, 38), cfg['hudSample']['room'], font=font(22), fill=ink)
d.text((1234, 75), 'Esc  일시정지', font=font(14), fill=muted, anchor='rt')

panel((26, 608, 333, 694))
portrait = sheet.crop((0, 0, source_size, source_size)).resize((74, 74), Image.Resampling.LANCZOS)
ui.alpha_composite(portrait, (37, 611))
d = ImageDraw.Draw(ui)
d.text((122, 619), cfg['hudSample']['element'], font=font(24), fill=ink)
d.text((123, 656), '보유 원소 없음', font=font(15), fill=muted)

panel((610, 620, 1254, 694))
def key(x, label, action, key_width, color=ink):
    d.rounded_rectangle((x, 637, x + key_width, 677), radius=6, fill='#35483a', outline='#738268')
    d.text((x + key_width / 2, 657), label, font=font(16), fill=color, anchor='mm')
    d.text((x + key_width + 10, 657), action, font=font(16), fill=color, anchor='lm')

key(626, 'Q / E', '원소 선택', 58, muted)
key(801, 'F', '먹기', 36)
key(908, 'Space', '기본 공격', 65)
key(1111, 'R', '스킬 없음', 36, '#94a48d')
screen = Image.alpha_composite(screen, ui).convert('RGB')
path = OUT / 'obstacle-room-ingame-preview.png'
if __name__ == '__main__':
    screen.save(path)
    print(f'Ingame composition: {W}x{H}, {view_w}x{view_h} visible units of 30x30; player height {screen_unit:g}px')
    print(f'Camera crop in source pixels: {crop}; player screen center: {px:g},{py:g}')
    print(path)
