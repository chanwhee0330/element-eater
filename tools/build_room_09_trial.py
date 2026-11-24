"""9번 방의 상급 퍼즐 배치와 공통 석재 지형을 내보낸다."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance

from dungeon_terrain import DungeonTerrain


OUT = Path(__file__).resolve().parents[1] / 'assets/maps/room-09'
UNIT, ORIGIN = 30, (120, 65)
FLOOR = [
    (18,1,21,4), (14,3,25,8), (16,8,23,14), (17,14,22,25),
    (4,10,11,15), (5,15,9,19), (4,18,17,23), (11,11,16,14),
    (23,11,28,14), (28,10,35,14), (31,14,35,20), (22,19,25,23), (25,20,35,27),
    (25,27,27,28),
]
WEIGHT_WALLS = [
    (0,4), (1,0), (1,5), (2,0), (4,4), (5,1), (6,0),
    (6,3), (6,4), (8,3), (9,1), (9,3), (9,4),
]
COVER = [
    (15.2,5,16.75,5.65), (22.25,5,23.8,5.65), (10.4,19.3,12.6,20),
    (6.2,11.45,7.4,12.05), (5,17.65,6.65,18), (7.9,17.65,9,18),
    *[(25+x,20+y,26+x,21+y) for x,y in WEIGHT_WALLS],
]
DOOR = [670,67,740,151]
POWER_GATE = (16,8.02,23,8.6)
RETURN_GATES = [(12.25,11,12.72,14), (25.3,11,25.77,14)]
SERVICE_GATE = (31,14.05,35,14.55)
DRAIN_GATE = (5,17.65,9,18)
WHEEL_GATE = (31,19.15,35,19.68)
WHEEL_OPENING = (32.5,33.5)
DRAIN_SECONDS = 2.2
DRAIN_PATH = [
    (7.25,18.15), (7.25,20.65), (13.5,20.65), (13.5,21.4),
    (28,21.4), (28,22.5), (31.5,22.5),
]
WIRES = [
    [(7.65,11.15),(7.65,12.65),(16.7,12.65),(16.7,10.55),(19.5,10.55)],
    [(30.35,11.15),(30.35,12.65),(22.3,12.65),(22.3,10.55),(19.5,10.55)],
    [(19.5,10.55),(19.5,3.2)],
]
WATER_PATH = [
    (9.5,11.65), (9.5,13.45), (34.25,13.45), (34.25,19.4), (33.8,19.4),
]
POWER_PATH = [
    (29.2,12.85), (29.2,12.65), (22.3,12.65), (22.3,10.55), *reversed(WIRES[0]),
]
RUNES = ('△', '□', '◇')
POWER_TARGETS = (3, 1, 2)
RUNE_HINTS = ((2,20.59,14.5), (0,20.59,15.5), (1,20.59,16.5), (0,5.5,12.5))
RUNE_GROOVES = (
    ((0,-10),(7,1),(-7,1)),
    ((-6,-10),(6,-10),(6,2),(-6,2)),
    ((0,-11),(7,-4),(0,3),(-7,-4)),
)


def carve_hint(art, index, floor_x, floor_y):
    x, y = art.point(floor_x, floor_y)
    left, top = x-10, y-14
    stone = art.image.crop((left, top, x+11, y+13))
    relief = ImageEnhance.Brightness(stone)
    count = POWER_TARGETS[index]
    for offset, brightness in ((1,1.26), (0,.5)):
        cut = [(10+u+offset, 14+v+offset) for u,v in RUNE_GROOVES[index]]
        mask = Image.new('L', stone.size)
        draw = ImageDraw.Draw(mask)
        draw.line([*cut, cut[0]], fill=255, width=2, joint='curve')
        for dot in range(count):
            px = 10+3*(2*dot-count+1)+offset
            py = 22+offset
            draw.ellipse((px-2, py-2, px+2, py+2), fill=255)
        art.image.paste(relief.enhance(brightness), (left, top), mask)


def build():
    art = DungeonTerrain(UNIT, ORIGIN, FLOOR, 909, (24,17,22), (1,18,21))
    art.rug(18.85,3,20.15,25)
    art.rims()
    for l,t,r,b in COVER:
        x,y = art.point(l,t)
        xx,yy = art.point(r,b)
        art.ledge(x,y,xx-x,yy-y)
    art.door(DOOR,(600,810))
    for wire in WIRES:
        path = [art.point(*p) for p in wire]
        for width, color in ((6,'#30242c'), (3,'#8d684e'), (1,'#b49171')):
            art.draw.line(path, fill=color, width=width, joint='curve')
    drain = [art.point(*p) for p in reversed(DRAIN_PATH)]
    for width, color in ((8,'#3a3345'),(4,'#646275'),(2,'#526977')):
        art.draw.line(drain, fill=color, width=width, joint='curve')
    for index, x, y in RUNE_HINTS:
        carve_hint(art, index, x, y)
    art.image.save(OUT/'trial-terrain.png', optimize=True)

    enemies = [('water','ranged',16.65,4.71), ('water','ranged',22.35,4.71), ('fire','melee',19.5,7.1)]
    tile_ids = dict(floor=0,crackedFloor=1,mossFloor=2,wall=3,pit=4,spikes=5)
    data = {
        'id':'room-09', 'name':'삼중 성문', 'columns':36, 'rows':28, 'tileIds':tile_ids,
        'tiles':[[0 if (x,y) in art.cells else 4 for x in range(36)] for y in range(28)],
        'heroReferenceHeight':89,
        'preview':{'playerSpeed':3.5,'meleeSpeed':2,'fallSeconds':.65},
        'playerSpawn':{'x':19.5,'y':23.75,'facing':'up'},
        'plannedExit':{'x':19.5,'y':2.65},
        'aggroTrigger':{'x':14,'y':3,'width':11,'height':5.2},
        'enemies':[{'id':f'{role}-{i}','x':x,'y':y,'element':elem,'behaviorType':role,'facing':'down'}
                   for i,(elem,role,x,y) in enumerate(enemies,1)],
        'referenceArt':{'image':'trial-terrain.png','minimumScale':1.45,'pixelsPerTile':UNIT,
                        'originPixels':ORIGIN,'walkable':FLOOR,'cover':COVER,
                        'coverPixels':[[*art.point(l,t),*art.point(r,b)] for l,t,r,b in COVER],
                        'doorPixels':DOOR,'walledBoundary':True},
        'stonePuzzle':{'start':[27.5,24.5],'plate':[31.5,22.5],'reset':[26.5,27.45],
                       'gate':DRAIN_GATE,'gatePixels':[*art.point(*DRAIN_GATE[:2]),*art.point(*DRAIN_GATE[2:])],
                       'centeredSlide':True, 'yard': [25,20,35,27]},
        'fireBarriers':[(5,15.92,9,16.42)],
        'vineGate':{'x':5,'y':14.75,'width':4,'height':.66,'burnDuration':.675},
        'powerPuzzle':{'switch':[19.5,12.15], 'conductors':[(7.65,11.15),(19.5,10.55),(30.35,11.15)],
                       'targets':POWER_TARGETS,'gate':POWER_GATE,
                       'gatePixels':[*art.point(*POWER_GATE[:2]),*art.point(*POWER_GATE[2:])],
                       'centeredSlide':True},
        'trial':{'basin':[6.65,16.42,7.9,18.12], 'returns':RETURN_GATES, 'serviceGate':SERVICE_GATE,
                 'switches':[(9.5,11.65),(29.2,12.85)], 'lasers':[(34.88,31.12,16.55)],
                 'wallSlot':[33.1,16.55], 'laserSweep':[.95,3.2],
                 'drainSeconds':DRAIN_SECONDS, 'drainPath':DRAIN_PATH,
                 'waterPath':WATER_PATH, 'powerPath':POWER_PATH,
                 'wheelGate':WHEEL_GATE, 'wheelOpening':WHEEL_OPENING,
                 'runes':RUNES},
        'layoutRevision':5,
    }
    (OUT/'room-09.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    build()
