"""증기 정원의 석재 지형과 상태별 오브젝트 시트를 만든다 (Pillow)."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from dungeon_terrain import DungeonTerrain


ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'assets/maps/room-07'
UNIT = 34
ORIGIN = (108, 83)
FLOOR = [
    (16, 20, 20, 24), (13, 11, 23, 21), (15, 4, 21, 12), (16, 1, 20, 5),
    (1, 15, 10, 22), (6, 10, 10, 16), (1, 6, 11, 11), (10, 7, 16, 10),
    (9, 17, 14, 20), (26, 15, 35, 22), (26, 10, 30, 16), (25, 6, 35, 11),
    (20, 7, 26, 10), (22, 17, 27, 20),
]
PLANTERS = [(1.35, 6.8, 3, 10.6), (3.35, 6.55, 7.05, 7.5), (1.45, 15.55, 3, 17.35),
            (1.45, 19.1, 3.3, 21.65), (7.55, 20.6, 9.6, 21.58), (10.95, 7.28, 12.65, 7.94),
            (13.25, 11.6, 14.25, 13.8), (21.75, 11.6, 22.75, 13.8),
            (13.22, 20.1, 15.75, 20.77), (20.25, 20.1, 22.78, 20.77)]
POOLS = [(30.9, 6.45, 34.45, 7.55), (33.05, 8.05, 34.65, 10.65), (32.9, 19.15, 34.65, 21.55),
         (26.35, 20.55, 28.35, 21.6), (23.55, 7.27, 24.95, 7.95)]
FOUNTAIN = (16.25, 12.85, 19.75, 15.62)
FIRE = (16, 21.02, 20, 21.79)
WHEEL, PUMP = (8.7, 8.45), (31.3, 8.45)
GATES = [(15, 10.22, 21, 10.95), (13.36, 7, 13.84, 10), (22.16, 7, 22.64, 10)]
LIGHTS = [(16.22, 11.52), (19.78, 11.52), (16.25, 23.1), (19.75, 23.1), (16.24, 4.7), (19.76, 4.7)]
WIRES = [[WHEEL, (12.6, 8.45), (12.6, 9.66), (16.22, 9.66), LIGHTS[0]],
         [PUMP, (23.4, 8.45), (23.4, 9.66), (19.78, 9.66), LIGHTS[1]],
         [(18, 11.52), (18, 2.35)]]


def point(x, y):
    return round(ORIGIN[0] + x * UNIT), round(ORIGIN[1] + y * UNIT)


def rect(bounds):
    return (*point(*bounds[:2]), *point(*bounds[2:]))


def inside(x, y, bounds):
    return any(l <= x < r and t <= y < b for l, t, r, b in bounds)


def terrain():
    terrain = DungeonTerrain(UNIT, ORIGIN, FLOOR, 70731, (23,16,20), (1,16,20))
    terrain.rug(17.35, 4, 18.65, 10)
    terrain.rug(17.35, 21, 18.65, 24)
    im, d = terrain.image, terrain.draw
    for wire in WIRES:
        for width, color in ((7, '#282d31'), (3, '#8a7955'), (1, '#aa9270')):
            d.line([point(*p) for p in wire], fill=color, width=width, joint='curve')
    l,t,r,b = rect(FIRE)
    d.rectangle((l,t,r,b), fill='#393c3e', outline='#8b8172', width=2)
    for x in range(l+6,r-4,10):
        d.line((x,t+4,x,b-4), fill='#262a2e', width=3)
    im.save(MAP / 'garden-terrain.png', optimize=True)


def sheet_frame(kind, i, active):
    im = Image.new('RGBA', (128, 96))
    d = ImageDraw.Draw(im)
    phase = math.tau * i / 12
    if kind in ('pool', 'fountain'):
        ellipse = kind == 'fountain'
        shape = d.ellipse if ellipse else lambda bounds, **kw: d.rounded_rectangle(bounds, 12, **kw)
        shape((1, 6, 126, 93), fill='#282338')
        shape((1, 2, 126, 87), fill='#57516d', outline='#8e8095', width=3)
        shape((7, 8, 120, 81), fill='#225f69', outline='#153a45', width=3)
        for line in range(8):
            if ellipse:
                spread = ((line + i / 12) / 8) * 40
                d.arc((64-spread,40-spread*.67,64+spread,40+spread*.67), 18*line, 220+18*line,
                      fill=(116, 196, 199, max(30, round(205-3*spread))))
            else:
                y = 17 + 7*line
                for j in range(5):
                    x = 12 + (21*j + 3*line + 2*i) % 100
                    d.line((x,y,min(x+11,114),y), fill=('#498a91', '#77b7b4', '#316f79')[j%3], width=2)
        if ellipse:
            d.ellipse((50,32,78,55), fill='#647873', outline='#b1bbb0', width=2)
            for j in range(5):
                x = 64 + (j-2)*10
                h = 12 + round(5*math.sin(phase + .8*j))
                d.line((64,42,64+(j-2)*4,h,x,29), fill='#80d4dc', width=2)
                d.point((x,33+i%4), fill='#c7f2e7')
    elif kind == 'planter':
        d.rounded_rectangle((1, 6, 126, 94), 10, fill='#302739')
        d.rounded_rectangle((1, 1, 126, 86), 10, fill='#5e5269', outline='#8c7c8c', width=3)
        d.rounded_rectangle((8, 9, 119, 80), 6, fill='#263b31')
        for j in range(12):
            x, y = 17+19*(j%6), 27+32*(j//6)
            dx = round(4*math.sin(phase+j*.62))
            d.line((x,y+12,x+dx,y), fill='#456644', width=3)
            d.ellipse((x+dx-7,y-5,x+dx+1,y+1), fill='#799c63')
            d.ellipse((x+dx,y-3,x+dx+7,y+4), fill='#598451')
            if j % 3 != 1:
                d.ellipse((x+dx-4,y-8,x+dx+3,y-2), fill=('#d492aa','#e5bb83')[j%2])
                d.point((x+dx,y-5),fill='#ffdc9e')
    else:
        d.ellipse((42,64,86,90), fill='#283a36')
        d.rounded_rectangle((49,45,79,80),5,fill='#62604c',outline='#ad9b73',width=3)
        glow = 135 + round(56*math.sin(phase))
        color = (251, 174+glow//4, 97) if active else (130+glow//4, 104+glow//4, 73)
        d.ellipse((53,36,75,61),fill=color,outline='#d1b57b',width=2)
    return im


def sprites():
    kinds = ('pool', 'fountain', 'planter', 'wheel', 'pump', 'lamp')
    sheet = Image.new('RGBA', (12*128, 9*96))
    # PixelFX에서 만든 장치 행을 유지하고 정원 배경 행만 다시 그린다.
    with Image.open(MAP / 'garden-objects.png') as existing:
        hardware = existing.convert('RGBA')
    clips = {}
    row = 0
    for kind in kinds:
        for active in ((False, True) if kind in ('wheel', 'pump', 'lamp') else (False,)):
            clips[kind + ('-active' if active else '')] = row
            for i in range(12):
                x, y = i*128, row*96
                frame = (hardware.crop((x,y,x+128,y+96)) if kind in ('wheel', 'pump')
                         else sheet_frame(kind, i, active))
                sheet.alpha_composite(frame, (x,y))
            row += 1
    sheet.save(MAP / 'garden-objects.png', optimize=True)
    (MAP/'garden-objects.json').write_text(json.dumps({'image': 'garden-objects.png', 'frameSize': [128,96],
                                                       'frames': 12, 'fps': 9, 'rows': clips}, indent=2)+'\n')


def write_map():
    tile_ids = dict(floor=0, crackedFloor=1, mossFloor=2, wall=3, pit=4, spikes=5)
    fighters = [(3.65,18,'wind','ranged'), (6.9,16.45,'wind','melee'), (6.15,20.8,'wind','melee'),
                (31.9,17.7,'fire','ranged'), (28.35,16.45,'fire','melee'), (29.85,20.8,'fire','ranged')]
    cover = [*PLANTERS, *POOLS, FOUNTAIN]
    data = {
        'id': 'room-07', 'name': '증기 수문 정원', 'columns': 36, 'rows': 24, 'tileIds': tile_ids,
        'tiles': [[3 if inside(x+.5,y+.5,cover) else 0 if inside(x+.5,y+.5,FLOOR) else 4
                   for x in range(36)] for y in range(24)],
        'heroReferenceHeight': 89, 'preview': {'playerSpeed': 3.5, 'meleeSpeed': 2, 'fallSeconds': .65},
        'playerSpawn': {'x': 18, 'y': 22.75, 'facing': 'up'}, 'plannedExit': {'x': 18, 'y': 1.85},
        'aggroTrigger': {'x': 0, 'y': 14, 'width': 36, 'height': 7},
        'enemies': [{'id': f'{behavior}-{i}', 'element': element, 'behaviorType': behavior,
                     'x': x, 'y': y, 'facing': 'down'} for i,(x,y,element,behavior) in enumerate(fighters,1)],
        'referenceArt': {'image': 'garden-terrain.png', 'pixelsPerTile': UNIT, 'originPixels': ORIGIN,
                         'minimumScale': 1.36, 'walkable': FLOOR, 'cover': cover, 'coverPixels': [],
                         'walledBoundary': True, 'doorPixels': [686, 94, 754, 177],
                         'wallOpenings': [(24, 16, 20), (1, 16, 20)], 'doorWallPixels': (652, 788)},
        'fireBarriers': [FIRE],
        'vineGate': {'x': 6, 'y': 13.02, 'width': 4, 'height': .68, 'burnDuration': .675},
        'sluice': {'wheel': WHEEL, 'pump': PUMP, 'gate': GATES[0], 'returnGates': GATES[1:],
                   'garden': {'planters': PLANTERS, 'pools': POOLS, 'fountain': FOUNTAIN,
                              'lamps': LIGHTS, 'wires': WIRES}},
        'layoutRevision': 4,
    }
    (MAP/'room-07.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    terrain()
    sprites()
    write_map()
