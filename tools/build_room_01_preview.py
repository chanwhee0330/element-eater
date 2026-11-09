"""기존 타일·캐릭터로 첫 방 배치 PNG/JSON 생성. 본게임·전투 구현 아님."""
from collections import Counter, deque
from pathlib import Path
import json
import random
import base64
from PIL import Image, ImageDraw, ImageFont, ImageOps
from room_01_decor import apply_decorations

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/maps/room-01'
OUT = ROOT / 'outputs/previews/room-01'


def main():
    layout = json.loads((ASSETS / 'source/layout.json').read_text(encoding='utf-8'))
    cols, rows, unit = (layout[k] for k in ('columns', 'rows', 'unitPixels'))
    tile_ids = dict(floor=0, crackedFloor=1, mossFloor=2, wall=3, pit=4, spikes=5)
    atlas = Image.open(ROOT / 'assets/maps/obstacle-room/obstacle-room-tiles.png').convert('RGB')
    tiles = [atlas.crop((i % 2 * unit, i // 2 * unit, (i % 2 + 1) * unit, (i // 2 + 1) * unit)) for i in range(6)]
    rng = random.Random(layout['seed'])
    grid = []
    for y in range(rows):
        row = []
        for x in range(cols):
            chance = rng.random()
            row.append(tile_ids[layout['defaultTile']])
        grid.append(row)
    for region in layout['floorRegions']:
        for y in range(region['y'], region['y'] + region['height']):
            for x in range(region['x'], region['x'] + region['width']):
                chance = rng.random()
                grid[y][x] = 2 if chance < .04 else 1 if chance > .94 else 0
    for region in layout['regions']:
        for y in range(region['y'], region['y'] + region['height']):
            for x in range(region['x'], region['x'] + region['width']):
                assert 0 < x < cols - 1 and 0 < y < rows - 1
                assert grid[y][x] in (0, 1, 2), '배치 영역 중복'
                grid[y][x] = tile_ids[region['kind']]

    # 위험 지형을 밟지 않고 모든 배치 지점에 접근 가능한지 검사한다.
    def cell(actor):
        return int(actor['x']), int(actor['y'])
    start = cell(layout['playerSpawn'])
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] < 3 and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    assert Counter(e['behaviorType'] for e in layout['enemies']) == {'melee': 2, 'ranged': 2}
    assert all(e['element'] == 'neutral' for e in layout['enemies'])
    for actor in [layout['playerSpawn'], *layout['enemies'], layout['plannedExit']]:
        assert grid[int(actor['y'])][int(actor['x'])] < 3 and cell(actor) in seen
    assert all(grid[y][x] < 3 for y in range(18, 21) for x in range(8, 12))
    assert all(grid[y][8] == grid[y][11] == 4 for y in range(11, 17))

    backdrop_recipe = json.loads((ASSETS / 'source/backdrop.json').read_text(encoding='utf-8'))
    viewport = backdrop_recipe['viewport']
    abyss = Image.open(ASSETS / 'source' / backdrop_recipe['source']).convert('RGB')
    abyss = ImageOps.fit(abyss, (viewport['width'], viewport['height']), Image.Resampling.LANCZOS)
    abyss.save(ASSETS / 'room-01-backdrop.png')
    # 화면 여백과 맵 내부 구멍을 같은 원경의 같은 좌표에서 잘라 이음새를 없앤다.
    box = (viewport['left'], viewport['top'], viewport['left']+cols*viewport['unit'], viewport['top']+rows*viewport['unit'])
    background = abyss.crop(box).resize((cols * unit, rows * unit), Image.Resampling.LANCZOS)
    for y, row in enumerate(grid):
        for x, tile_id in enumerate(row):
            if tile_id != 4:
                background.paste(tiles[tile_id], (x * unit, y * unit))
    edge = ImageDraw.Draw(background)
    for y, row in enumerate(grid):
        for x, tile_id in enumerate(row):
            if tile_id == 4:
                continue
            x0, y0, x1, y1 = x * unit, y * unit, (x + 1) * unit, (y + 1) * unit
            if y + 1 < rows and grid[y + 1][x] == 4:
                edge.rectangle((x0, y1, x1 - 1, y1 + 16), fill='#443729')
                edge.line((x0, y1 + 17, x1 - 1, y1 + 17), fill='#0b1016', width=5)
                edge.line((x0, y1 - 3, x1 - 1, y1 - 3), fill='#b2946d', width=5)
            if y > 0 and grid[y - 1][x] == 4:
                edge.line((x0, y0 + 2, x1 - 1, y0 + 2), fill='#c2a782', width=5)
            if x > 0 and grid[y][x - 1] == 4:
                edge.line((x0 + 2, y0, x0 + 2, y1 - 1), fill='#b2946d', width=5)
            if x + 1 < cols and grid[y][x + 1] == 4:
                edge.line((x1 - 3, y0, x1 - 3, y1 - 1), fill='#b2946d', width=5)
    background = apply_decorations(background, grid, unit, ASSETS / 'source')
    background.save(ASSETS / 'room-01.png')
    atlas.save(ASSETS / 'room-01-tiles.png')
    hero_dir = ROOT / 'assets/sprites/hero/neutral'
    reference = Image.open(hero_dir / 'hero-neutral-idle.png').convert('RGBA').crop((0, 0, 128, 128))
    bounds = reference.getchannel('A').point(lambda value: 255 if value >= 96 else 0).getbbox()
    data = dict(layout, tileIds=tile_ids, tiles=grid, image='room-01.png', tileAtlas='room-01-tiles.png',
                heroReferenceHeight=bounds[3] - bounds[1],
                backdropImage='room-01-backdrop.png', backdropViewport=viewport,
                solidTileIds=[3], hazardTileIds=[4, 5],
                pitSource='../obstacle-room/source/pit-source.png',
                decorations={'source': 'source/decorations.json', 'atlas': 'source/decor-atlas-v1.png', 'collision': False},
                rendering={'pit': '연결된 허공 하나와 바닥 경계만 그린다. room-01.png를 배경으로 사용.'},
                scope='Python main.py: 첫 방 이동·무속성 전투·체력/HUD·출구/첫 방 클리어. 별도 HTML은 이동·추격 시연만 제공. 원소·지형 피해·다른 방 미구현.')
    (ASSETS / 'room-01.json').write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    OUT.mkdir(parents=True, exist_ok=True)
    board = Image.new('RGB', (1000, 1224), '#15241e')
    draw = ImageDraw.Draw(board)
    def font(size):
        return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', size)
    draw.text((48, 26), 'ROOM 01  /  첫 번째 방', fill='#f4f0df', font=font(31))
    draw.text((48, 74), '20 × 22칸  /  시작 섬 → 좁은 연결로 → 위쪽 전투 구역', fill='#bdd0b9', font=font(19))
    left, top, screen_unit = 60, 124, 44
    board.paste(background.resize((cols * screen_unit, rows * screen_unit), Image.Resampling.LANCZOS), (left, top))
    def point(x, y):
        return left + x * screen_unit, top + y * screen_unit
    def label(text, x, y, color='#e3e8d5'):
        px, py = point(x, y)
        bounds = draw.textbbox((px, py), text, font=font(16), anchor='mm')
        draw.rounded_rectangle((bounds[0] - 9, bounds[1] - 5, bounds[2] + 9, bounds[3] + 5), 7, fill='#17221e', outline=color, width=1)
        draw.text((px, py), text, fill=color, font=font(16), anchor='mm')

    # 전체 방과 기존 맵의 공통 배율. 적마다 외곽 크기에 맞춰 재확대하지 않는다.
    scale = screen_unit / (bounds[3] - bounds[1])
    def actor(record, is_player=False):
        if is_player:
            sheet_path, frame, pivot = hero_dir / 'hero-neutral-idle.png', 128, (64, 114)
        else:
            kind = record['behaviorType']
            sheet_path = ROOT / f'assets/sprites/enemies/elemental-v1/neutral/{kind}/enemy-neutral-{kind}-idle.png'
            frame, pivot = 160, (80, 138)
        row = ['down', 'left', 'right', 'up'].index(record['facing'])
        sprite = Image.open(sheet_path).convert('RGBA').crop((0, row * frame, frame, (row + 1) * frame))
        sprite = sprite.resize((round(frame * scale), round(frame * scale)), Image.Resampling.LANCZOS)
        px, py = point(record['x'], record['y'])
        draw.ellipse((px - 12, py - 4, px + 12, py + 4), fill='#414539')
        board.paste(sprite, (round(px - pivot[0] * scale), round(py - pivot[1] * scale)), sprite)
    for enemy in layout['enemies']:
        actor(enemy)
        role = '근접' if enemy['behaviorType'] == 'melee' else '원거리'
        label(role + ' ' + enemy['id'][-1], enemy['x'], enemy['y'] + .7, '#f3c99c' if role == '근접' else '#b9d5ed')
    actor(layout['playerSpawn'], True)
    label('시작 섬', 10, 20.5, '#c9edac')
    for x in (5, 15):
        label('낭떠러지', x, 14, '#c8bdba')
    label('가시', 7.8, 18.1, '#f0b2a1')
    label('가시', 12.2, 18.1, '#f0b2a1')
    label('벽', 10, 7, '#d9ceb0')
    # 큰 구역에 들어서는 경계. 통행 가능한 바닥 위 표시이며 실제 장벽이 아니다.
    tx1, ty = point(9, 11)
    tx2, _ = point(11, 11)
    draw.line((tx1, ty, tx2, ty), fill='#edc973', width=3)
    label('여기부터 근접 적 추격', 10, 12, '#edc973')
    ex, ey = point(layout['plannedExit']['x'], layout['plannedExit']['y'])
    draw.line((ex, ey + 12, ex, ey - 12), fill='#d9edb2', width=3)
    draw.line((ex - 7, ey - 5, ex, ey - 12, ex + 7, ey - 5), fill='#d9edb2', width=3)
    label('출구 예정', 10, 3.6, '#d9edb2')
    draw.text((48, 1120), '무속성 근접 2 · 원거리 2  /  큰 구역 진입 시 근접 추격 시작', fill='#e0e6cf', font=font(19))
    draw.text((48, 1160), '맵 면적 약 51% 축소 · 연결로 양옆과 바닥 바깥은 낭떠러지', fill='#bdd0b9', font=font(18))
    draw.text((48, 1197), 'Python 전투 실행: main.py / 별도 HTML은 이동·추격 시연', fill='#a4b59d', font=font(14))
    board.save(OUT / 'room-01-layout.png')
    paths = {'world': ASSETS / 'room-01.png', 'fallback': OUT / 'room-01-layout.png'}
    paths.update({f'hero-{state}': hero_dir / f'hero-neutral-{state}.png' for state in ('idle', 'walk')})
    for kind, states in [('melee', ('idle', 'walk')), ('ranged', ('idle',))]:
        for state in states:
            paths[f'{kind}-{state}'] = ROOT / f'assets/sprites/enemies/elemental-v1/neutral/{kind}/enemy-neutral-{kind}-{state}.png'
    images = {key: 'data:image/png;base64,' + base64.b64encode(path.read_bytes()).decode() for key, path in paths.items()}
    html = (ROOT / 'tools/room_01_preview.html').read_text(encoding='utf-8')
    html = html.replace('/*ROOM_LOGIC*/', (ROOT / 'tools/room_01_logic.js').read_text(encoding='utf-8'))
    html = html.replace('/*ROOM_DATA*/null', json.dumps(data, ensure_ascii=False))
    html = html.replace('/*ROOM_IMAGES*/null', json.dumps(images))
    html = html.replace('FALLBACK_IMAGE', images['fallback'])
    (OUT / 'preview.html').write_text(html, encoding='utf-8')
    print(f'첫 방 생성: {cols}×{rows}, 무속성 적 4, 안전 경로 검사 통과')


if __name__ == '__main__':
    main()
