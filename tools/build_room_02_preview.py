"""실행 게임과 공유하는 두 번째 방 배치 데이터·정적 안내 이미지 생성."""
from collections import Counter, deque
from pathlib import Path
import json
import random
from PIL import Image, ImageDraw, ImageFont
from room_01_decor import apply_decorations

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/maps/room-02'
OUT = ROOT / 'outputs/previews/room-02'


def main():
    layout = json.loads((ASSETS / 'source/layout.json').read_text(encoding='utf-8'))
    cols, rows, unit = (layout[k] for k in ('columns', 'rows', 'unitPixels'))
    atlas = Image.open(ROOT / 'assets/maps/obstacle-room/obstacle-room-tiles.png').convert('RGB')
    tiles = [atlas.crop((i%2*unit, i//2*unit, (i%2+1)*unit, (i//2+1)*unit)) for i in range(6)]
    grid = [[4]*cols for _ in range(rows)]
    rng = random.Random(layout['seed'])
    for region in layout['floorRegions']:
        for y in range(region['y'], region['y']+region['height']):
            for x in range(region['x'], region['x']+region['width']):
                assert grid[y][x] == 4
                n = rng.random()
                grid[y][x] = 2 if n < .035 else 1 if n > .95 else 0
    for region in layout['regions']:
        for y in range(region['y'], region['y']+region['height']):
            for x in range(region['x'], region['x']+region['width']):
                assert grid[y][x] < 3
                grid[y][x] = 3

    def cell(actor):
        return int(actor['x']), int(actor['y'])
    start = cell(layout['playerSpawn'])
    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if 0 <= nx < cols and 0 <= ny < rows and grid[ny][nx] < 3 and (nx,ny) not in seen:
                seen.add((nx,ny))
                queue.append((nx,ny))
    assert Counter(e['element'] for e in layout['enemies']) == {'neutral':2, 'fire':2}
    assert Counter((e['element'],e['behaviorType']) for e in layout['enemies']) == {
        ('neutral','melee'):1, ('neutral','ranged'):1, ('fire','melee'):1, ('fire','ranged'):1}
    for actor in [layout['playerSpawn'], *layout['enemies'], *layout['elementSources'], layout['plannedExit']]:
        assert cell(actor) in seen and grid[int(actor['y'])][int(actor['x'])] < 3
    assert all(s['element'] == 'water' for s in layout['elementSources'])
    for a, b in zip(layout['suggestedRoute'], layout['suggestedRoute'][1:]):
        for t in range(101):
            x, y = a[0]+(b[0]-a[0])*t/100, a[1]+(b[1]-a[1])*t/100
            assert grid[int(y)][int(x)] < 3, ('동선이 벽/낭떠러지와 겹침', x, y)

    abyss = Image.open(ROOT / 'assets/maps/room-01/room-01-backdrop.png').convert('RGB')
    terrain = abyss.crop((140,64,140+cols*36,64+rows*36)).resize((cols*unit,rows*unit), Image.Resampling.LANCZOS)
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            if tile != 4:
                terrain.paste(tiles[tile], (x*unit,y*unit))
    edge = ImageDraw.Draw(terrain)
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            if tile == 4:
                continue
            x0,y0,x1,y1 = x*unit,y*unit,(x+1)*unit,(y+1)*unit
            if y+1 < rows and grid[y+1][x] == 4:
                edge.rectangle((x0,y1,x1-1,y1+16), fill='#443729')
                edge.line((x0,y1+17,x1-1,y1+17), fill='#10110e', width=5)
                edge.line((x0,y1-3,x1-1,y1-3), fill='#b2946d', width=5)
            if y > 0 and grid[y-1][x] == 4:
                edge.line((x0,y0+2,x1-1,y0+2), fill='#c2a782', width=5)
            if x > 0 and grid[y][x-1] == 4:
                edge.line((x0+2,y0,x0+2,y1-1), fill='#b2946d', width=5)
            if x+1 < cols and grid[y][x+1] == 4:
                edge.line((x1-3,y0,x1-3,y1-1), fill='#b2946d', width=5)
    terrain = apply_decorations(terrain, grid, unit, ASSETS / 'source')
    terrain.save(ASSETS / 'room-02.png')
    atlas.save(ASSETS / 'room-02-tiles.png')
    data = dict(layout, image='room-02.png', tileAtlas='room-02-tiles.png', tiles=grid,
                heroReferenceHeight=json.loads((ROOT / 'assets/maps/room-01/room-01.json').read_text(encoding='utf-8'))['heroReferenceHeight'],
                backdropImage='../room-01/room-01-backdrop.png',
                preview={'playerSpeed':3.5,'meleeSpeed':2,'fallSeconds':.65},
                aggroTrigger=layout['zones'][0], fireAggroTrigger=layout['zones'][2],
                tileIds=dict(floor=0,crackedFloor=1,mossFloor=2,wall=3,pit=4,spikes=5),
                solidTileIds=[3], hazardTileIds=[4],
                sourceIdleImage='../../items/elements/break-release-v3/sprites/water-idle.png')
    (ASSETS / 'room-02.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

    OUT.mkdir(parents=True,exist_ok=True)
    board = Image.new('RGB',(1000,1320),'#22221d')
    draw = ImageDraw.Draw(board)
    def font(size):
        return ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',size)
    draw.text((500,40),'ROOM 02  ·  물의 유적',fill='#eee4cb',font=font(30),anchor='mm')
    draw.text((500,83),'물 원소 획득  /  무속성 적 2 · 불 적 2  /  20 × 22칸',fill='#c0bba7',font=font(17),anchor='mm')
    left,top,su = 60,122,44
    board.paste(terrain.resize((cols*su,rows*su),Image.Resampling.LANCZOS),(left,top))
    def point(x,y):
        return left+x*su,top+y*su
    def label(text,x,y,color='#e6dcc4',size=15):
        px,py = point(x,y)
        box = draw.textbbox((px,py),text,font=font(size),anchor='mm')
        draw.rounded_rectangle((box[0]-8,box[1]-5,box[2]+8,box[3]+5),6,fill='#25271fe8',outline=color)
        draw.text((px,py),text,font=font(size),fill=color,anchor='mm')
    reference = Image.open(ROOT / 'assets/sprites/hero/neutral/hero-neutral-idle.png').convert('RGBA').crop((0,0,128,128))
    bounds = reference.getchannel('A').point(lambda a:255 if a>=96 else 0).getbbox()
    scale = su/(bounds[3]-bounds[1])
    def sprite(path,record,frame,pivot):
        sheet = Image.open(path).convert('RGBA')
        row = ['down','left','right','up'].index(record.get('facing','down'))
        crop = sheet.crop((0,row*frame,frame,(row+1)*frame))
        crop = crop.resize((round(frame*scale),round(frame*scale)),Image.Resampling.LANCZOS)
        px,py = point(record['x'],record['y'])
        draw.ellipse((px-11,py-3,px+11,py+4),fill='#505040')
        board.paste(crop,(round(px-pivot[0]*scale),round(py-pivot[1]*scale)),crop)
    # 파괴 전 항아리만 맵에 놓는다. 방출 구슬은 별도 획득 단계이며 중복 배치하지 않는다.
    for source in layout['elementSources']:
        sprite(ROOT / 'assets/items/elements/break-release-v3/sprites/water-idle.png',source,128,(64,114))
        label('물 원천',source['x'],source['y']+.55,'#a6d5e1')
    for e in layout['enemies']:
        sprite(ROOT / f'assets/sprites/enemies/elemental-v1/{e["element"]}/{e["behaviorType"]}/enemy-{e["element"]}-{e["behaviorType"]}-idle.png',e,160,(80,138))
        text = ('무속성' if e['element']=='neutral' else '불')+' '+('근접' if e['behaviorType']=='melee' else '원거리')
        label(text,e['x'],e['y']+.65,'#dfb793' if e['element']=='neutral' else '#f2ad8b')
    sprite(ROOT / 'assets/sprites/hero/neutral/hero-neutral-idle.png',layout['playerSpawn'],128,(64,114))
    label('시작',10,20.5,'#ced7af')
    label('물 획득 구역',10,12.75,'#a6d5e1',14)
    label('출구 예정',10,2.6,'#dfd1a4')
    ex,ey = point(10,3.3)
    draw.line((ex,ey+9,ex,ey-9),fill='#dfd1a4',width=2)
    draw.line((ex-5,ey-4,ex,ey-9,ex+5,ey-4),fill='#dfd1a4',width=2)
    steps = [('01  무속성 전투','아래 구역에서 기본 공격 익히기'),
             ('02  물 원소 획득','항아리 3회 공격 → 방출 구슬 F'),
             ('03  불 적 공략','물 기본 공격으로 불 약점 공략')]
    for i,(title,body) in enumerate(steps):
        x = 36+i*314
        draw.rounded_rectangle((x,1122,x+300,1211),10,fill='#303128',outline='#68624f')
        draw.text((x+150,1145),title,font=font(18),fill='#e5d5ad',anchor='mm')
        draw.text((x+150,1181),body,font=font(13),fill='#c6c5af',anchor='mm')
    draw.text((500,1243),'물 원천 2곳 · 좌우 우회로 · 중앙 엄폐 벽 · 바깥은 낭떠러지',font=font(16),fill='#c6c5af',anchor='mm')
    draw.text((500,1284),'승인 배치도 / Python에서 물 획득·전투·1→2번 방 전환·이어하기 지원',font=font(13),fill='#a7a68e',anchor='mm')
    board.save(OUT / 'room-02-layout.png')
    print('PASS: room-02 layout, neutral 2/fire 2, two reachable water sources, safe route and exit')


if __name__ == '__main__':
    main()
