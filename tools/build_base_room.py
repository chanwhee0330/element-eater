"""30×30 기본 맵과 플레이어 크기 비교 미리보기를 만든다. 본게임 구현과 별개다."""
from pathlib import Path
import argparse
import base64
import hashlib
import json
import random
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--hero-dir', type=Path, default=ROOT / 'assets/sprites/hero/neutral')
parser.add_argument('--variant', choices=['base', 'obstacles'], default='base')
args = parser.parse_args()
name = 'obstacle-room' if args.variant == 'obstacles' else 'base-room'
ASSETS = ROOT / 'assets/maps' / name
SOURCE = ASSETS / 'source'
PREVIEW = ROOT / 'outputs/previews' / name
hero_dir = args.hero_dir.resolve()
recipe = json.loads((SOURCE / 'recipe.json').read_text(encoding='utf-8'))
columns, rows, unit = recipe['columns'], recipe['rows'], recipe['unitPixels']
PREVIEW.mkdir(parents=True, exist_ok=True)

# Raw source tiles are only sliced/resized; the original artwork stays in source/.
source = Image.open(SOURCE / recipe['tileSource']).convert('RGB')
tiles = []
hazard_sources = {kind: Image.open(SOURCE / filename).convert('RGB')
                  for kind, filename in recipe.get('hazardSources', {}).items()}
atlas = Image.new('RGB', (unit * 2, unit * (3 if hazard_sources else 2)))
for index in range(4):
    x, y = index % 2, index // 2
    box = (round(x * source.width / 2), round(y * source.height / 2),
           round((x + 1) * source.width / 2), round((y + 1) * source.height / 2))
    tile = source.crop(box).resize((unit, unit), Image.Resampling.LANCZOS)
    tiles.append(tile)
    atlas.paste(tile, (x * unit, y * unit))
for index, kind in enumerate(['pit', 'spikes'], 4):
    if kind in hazard_sources:
        tile = hazard_sources[kind].resize((unit, unit), Image.Resampling.LANCZOS)
        tiles.append(tile)
        atlas.paste(tile, (index % 2 * unit, index // 2 * unit))
atlas_path = ASSETS / f'{name}-tiles.png'
atlas.save(atlas_path)

rng = random.Random(recipe['seed'])
wall = recipe['wallThicknessUnits']
grid = []
for y in range(rows):
    row = []
    for x in range(columns):
        if x < wall or y < wall or x >= columns - wall or y >= rows - wall:
            tile_id = 3
        else:
            chance = rng.random()
            near_wall = min(x, y, columns - 1 - x, rows - 1 - y) <= wall + 1
            tile_id = 2 if near_wall and chance < .15 else 1 if chance > .94 else 0
        row.append(tile_id)
    grid.append(row)

tile_ids = {'floor': 0, 'crackedFloor': 1, 'mossFloor': 2, 'wall': 3}
if hazard_sources: tile_ids.update(pit=4, spikes=5)
for region in recipe.get('regions', []):
    tile_id = tile_ids[region['kind']]
    for y in range(region['y'], region['y'] + region['height']):
        for x in range(region['x'], region['x'] + region['width']):
            assert wall <= x < columns-wall and wall <= y < rows-wall, region
            assert grid[y][x] in (0, 1, 2, tile_id), (region, x, y)
            grid[y][x] = tile_id

background = Image.new('RGB', (columns * unit, rows * unit))
for y, row in enumerate(grid):
    for x, tile_id in enumerate(row):
        background.paste(tiles[tile_id], (x * unit, y * unit))
for region in recipe.get('regions', []):
    if region['kind'] == 'pit':
        # A single cutout for each whole pit; no artificial internal rim seams between its cells.
        pit = hazard_sources['pit'].resize((region['width'] * unit, region['height'] * unit), Image.Resampling.LANCZOS)
        background.paste(pit, (region['x'] * unit, region['y'] * unit))
map_path = ASSETS / f'{name}.png'
background.save(map_path)

hero_meta = json.loads((hero_dir / 'hero-neutral-idle.json').read_text(encoding='utf-8'))
frame_size = hero_meta['frameSize']['width']
idle_sheet = Image.open(hero_dir / 'hero-neutral-idle.png').convert('RGBA')
reference = idle_sheet.crop((0, 0, frame_size, frame_size))
threshold = recipe['player']['referenceAlphaThreshold']
bounds = reference.getchannel('A').point(lambda value: 255 if value >= threshold else 0).getbbox()
assert bounds
body_height = bounds[3] - bounds[1]
center = {'x': (bounds[0] + bounds[2]) / 2, 'y': (bounds[1] + bounds[3]) / 2}
player = dict(recipe['player'])
player.update(spriteFrameSize=frame_size, referenceSolidHeightPixels=body_height,
              referenceCenterPixelsTopLeft=center,
              spritePivotPixelsTopLeft=hero_meta['frames']['down_0']['pivotPixelsTopLeft'],
              idleImage='../../sprites/hero/neutral/hero-neutral-idle.png',
              walkImage='../../sprites/hero/neutral/hero-neutral-walk.png')
data = {
    'schema': 'element-eater.tilemap.v1', 'id': recipe['id'], 'name': recipe['name'],
    'columns': columns, 'rows': rows, 'unitPixels': unit,
    'image': map_path.name, 'imageSize': {'width': background.width, 'height': background.height},
    'tileAtlas': atlas_path.name, 'tileIds': tile_ids,
    'tiles': grid, 'solidTileIds': [3], 'wallThicknessUnits': wall,
    'coordinateSystem': 'top-left origin; x right, y down; preview player position is reference-silhouette center',
    'player': player, 'units': '1 unit = neutral idle-down frame 0 visible height from leaves to feet',
    'scope': '기본 맵 크기 비교·이동 미리보기. 적·전투·원소·퍼즐·방 전환 미구현.',
    'generator': {'command': 'python tools/build_base_room.py', 'recipe': 'source/recipe.json', 'seed': recipe['seed']},
    'sha256': hashlib.sha256(map_path.read_bytes()).hexdigest(),
}
if hazard_sources:
    data.update(regions=recipe['regions'], previewLabels=recipe['previewLabels'],
                previewHazards=recipe['previewHazards'], hazardTileIds=[4,5],
                propImages={'pit': 'source/pit-source.png', 'spikes': 'source/spikes-source.png'},
                rendering={'pit': 'Draw one source prop over each entire pit region, not a separate rim per tile'},
                scope='장애물 배치·이동·추락 복귀·가시 접촉 점멸 예시. 체력 피해·적·전투·원소·퍼즐 미구현.')
    data['generator']['command'] += ' --variant obstacles'
(ASSETS / f'{name}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

images = {'world': base64.b64encode(map_path.read_bytes()).decode()}
images.update({state: base64.b64encode((hero_dir / f'hero-neutral-{state}.png').read_bytes()).decode()
               for state in ['idle', 'walk']})
script = (ROOT / 'tools/base_room_preview.js').read_text(encoding='utf-8')
script = script.replace('MAP_DATA', json.dumps(data, ensure_ascii=False)).replace('IMAGE_DATA', json.dumps(images))
html = (ROOT / 'tools/base_room_preview.html').read_text(encoding='utf-8').replace('PREVIEW_SCRIPT', script)
html = html.replace('MAP_TITLE', recipe['name']).replace('GRID_CHECKED', '' if hazard_sources else 'checked')
html = html.replace('HAZARD_HELP', ' 구멍: 낙하 후 안전 위치 복귀 · 가시: 접촉 점멸 예시' if hazard_sources else '')
(PREVIEW / f'{name}-preview.html').write_text(html, encoding='utf-8')

# Labeled, shareable overview. The environmental PNG above contains no player or measurement overlay.
font_path = Path('C:/Windows/Fonts/malgun.ttf')
def font(size):
    return ImageFont.truetype(str(font_path), size) if font_path.exists() else ImageFont.load_default(size=size)

board = Image.new('RGB', (1120, 1260), '#15241e')
draw = ImageDraw.Draw(board)
draw.text((48, 24), f'엘리먼트 이터 · {recipe["name"]}', fill='#f5efda', font=font(30))
draw.text((48, 70), '맵 30 × 30   /   플레이어 1', fill='#d8e4c0', font=font(22))
draw.text((48, 108), '비교 기준: 잎부터 발끝까지 높이 1 = 바닥 1칸', fill='#b7c9b2', font=font(16))
left, top, size = 88, 196, 960
board.paste(background.resize((size, size), Image.Resampling.LANCZOS), (left, top))
screen_unit = size / columns
for i in range(0, columns + 1, 5):
    x = round(left + i * screen_unit)
    y = round(top + i * screen_unit)
    if not hazard_sources:
        draw.line((x, top, x, top + size - 1), fill='#b5b09a', width=1)
        draw.line((left, y, left + size - 1, y), fill='#b5b09a', width=1)
    draw.text((x, top + size + 12), str(i), fill='#bacbb0', font=font(13), anchor='mt')
draw.line((left, top - 25, left + size, top - 25), fill='#a9c393', width=2)
draw.line((left - 26, top, left - 26, top + size), fill='#a9c393', width=2)
for x in [left, left + size]: draw.line((x, top - 32, x, top - 18), fill='#a9c393', width=2)
for y in [top, top + size]: draw.line((left - 33, y, left - 19, y), fill='#a9c393', width=2)
draw.text((left + size / 2, top - 42), '30', fill='#e5ebd1', font=font(19), anchor='mm')
draw.text((left - 48, top + size / 2), '30', fill='#e5ebd1', font=font(19), anchor='mm')
px = left + player['spawnCenter']['x'] * screen_unit
py = top + player['spawnCenter']['y'] * screen_unit
sprite_scale = screen_unit * player['heightUnits'] / body_height
sprite = reference.resize((round(frame_size * sprite_scale), round(frame_size * sprite_scale)), Image.Resampling.LANCZOS)
at = (round(px - center['x'] * sprite_scale), round(py - center['y'] * sprite_scale))
draw.ellipse((px - 9, py + 11, px + 9, py + 17), fill='#65634b')
board.paste(sprite, at, sprite)
draw.rectangle((px - 16, py - 16, px + 16, py + 16), outline='#fff5cb', width=1)
draw.line((px + 16, py - 16, px + 62, py - 50, px + 166, py - 50), fill='#fff5cb', width=2)
draw.rounded_rectangle((px + 64, py - 78, px + 197, py - 47), radius=5, fill='#24372a')
draw.text((px + 76, py - 74), '플레이어 1', fill='#fff5cb', font=font(18))
for label in recipe.get('previewLabels', []):
    ax, ay = left+label['anchor']['x']*screen_unit, top+label['anchor']['y']*screen_unit
    tx, ty = left+label['label']['x']*screen_unit, top+label['label']['y']*screen_unit
    draw.line((ax,ay,tx,ty),fill='#e9eed1',width=2)
    draw.rounded_rectangle((tx-36,ty-17,tx+36,ty+17),radius=5,fill='#24372a')
    draw.text((tx,ty),label['text'],fill='#fff5cb',font=font(18),anchor='mm')
footer = '전체 900칸 · 구멍 2곳 · 내부 벽 · 가시 2구역 · 중앙 안전 공간' if hazard_sources else '전체 900칸 · 외곽 벽 1칸 포함 · 내부 바닥 28×28칸'
draw.text((48, 1201), footer, fill='#b7c9b2', font=font(16))
board.save(PREVIEW / f'{name}-scale-preview.png')
print(f'{name}: {columns}x{rows} units, {background.width}x{background.height}px; player height 1 unit = {body_height} source pixels')
print(f'Map PNG/JSON, {len(tiles)}-tile atlas, offline WASD preview and scale comparison PNG saved ({name})')
