"""승인된 절벽 운반로의 지형, 장치 발광·충돌 효과 시트를 생성한다."""
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from dungeon_terrain import DungeonTerrain


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
OUT = ASSETS / 'maps/room-08'
UNIT, ORIGIN = 34, (108, 64)
FLOOR = [
    (16,22,20,25), (8,19,28,23), (15,16,21,20), (14,15,22,17),
    (4,7,11,17), (7,5,20,8), (15,7,20,11), (8,9,18,12), (15,11,18,15),
    (21,15,30,17), (27,7,30,16), (22,3,34,8), (24,1,28,4),
    (28,7,35,9), (32,8,35,13), (25,12,27,14), (30,9,31,11), (24,8,26,9),
]
COVER = [
    (8.5,19.4,9.4,20.45), (12.3,21.45,14.1,22.1), (22.35,20,23.4,20.85),
    (25.65,21.42,27.65,22.4), (4.3,8.0,5.15,10.1), (5.1,14.95,6.8,15.72),
    (7.2,5.27,9,5.98), (10.5,5.27,12.2,5.98), (14,5.27,15.7,5.98),
    (19.45,6.6,19.92,8.95), (25.05,12.9,26.45,13.6), (30.07,10.64,30.87,10.99),
    (22.4,4.2,23.48,5.04), (32.1,5.45,33.5,6.12), (34.11,9.45,34.75,10.82),
    (17,10,18,11), (27.03,13.36,27.56,14.04),
]
BRIDGE = (11,15,14,17)
GATES = [(22.23,15,22.85,17), (15,14.18,18,14.82)]
LASERS = [(32.5,26.9,11.52), (25.55,34.88,8.54)]
WALL_SLOTS = [
    {'position': (29.43,11.52), 'approach': (27,10.17,28.89,12.87)},
    {'position': (27.47,8.54), 'approach': (28.01,7.19,30,9.89)},
]
LAMPS = [(4.45,16.24), (7.27,6.22), (18.96,8.57), (24.55,4.14), (28.67,14.68),
         (34.48,12.44), (16.26,24.3), (19.73,24.3), (8.35,21.78), (27.65,22.13)]


def point(x, y):
    return round(ORIGIN[0]+x*UNIT), round(ORIGIN[1]+y*UNIT)


def box(bounds):
    return (*point(*bounds[:2]), *point(*bounds[2:]))


def terrain():
    banks = {(x, y) for x in (11, 14) for y in (15, 16)}
    terrain = DungeonTerrain(UNIT, ORIGIN, FLOOR, 808, (24,16,20), (1,24,28), open_banks=banks)
    terrain.rug(17.35, 19, 18.65, 25)
    terrain.rug(25.35, 3, 26.65, 7)
    terrain.rims()
    im, d = terrain.image, terrain.draw
    for bounds in COVER:
        l,t,r,b = box(bounds)
        terrain.ledge(l, t, r-l, b-t)
    wire = [point(*xy) for xy in ((16.5,13.5),(16.5,14.13),(17.8,14.13),(17.8,15.45),(22.5,15.45))]
    d.line(wire,fill='#2f292d',width=6)
    d.line(wire,fill='#a48058',width=2)
    for x in (10.72,14.28):
        for y in (15.23,16.77):
            d.rounded_rectangle(box((x-.18,y-.21,x+.18,y+.21)),4,fill='#47362c',outline='#d2a55f',width=2)
    markers = [(x-.33,y-.9,x+.33,y+.9) for x,y in (slot['position'] for slot in WALL_SLOTS)]
    for bounds in [*markers,(30.08,9.66,30.91,10.57)]:
        d.rounded_rectangle(box(bounds),4,fill='#4c4548',outline='#bf9f72',width=2)
    terrain.door((956, 78, 1028, 154), (924, 1060))
    im.convert('RGB').save(OUT/'quarry-terrain.png',optimize=True)


def make_laser_sheet():
    size, count = 64, 12
    rows = ('emitter', 'receiver', 'receiver-cut', 'impact')
    sheet = Image.new('RGBA',(size*count,size*len(rows)))
    for row,name in enumerate(rows):
        for frame in range(count):
            im = Image.new('RGBA',(size,size))
            d = ImageDraw.Draw(im)
            phase = frame*math.tau/count
            pulse = round(17*math.sin(phase))
            if name == 'impact':
                for i in range(7):
                    angle = -math.pi/2+i*.51
                    distance = (frame+i*3)%count * 2
                    x = round(32+math.cos(angle)*distance)
                    y = round(32+math.sin(angle)*distance)
                    fade = max(46,250-distance*8)
                    d.line((x,y,x+3,y+(-2 if i<3 else 2)),fill=(255,151+4*i,65,fade),width=2)
                d.ellipse((27,27,37,37),fill=(255,214,123,175+pulse))
                d.ellipse((29,29,35,35),fill='#fff3bf')
            else:
                d.ellipse((5,51,58,62),fill=(26,22,29,160))
                d.rounded_rectangle((9,10,54,55),7,fill='#4c3a49',outline='#b6966d',width=3)
                d.rounded_rectangle((15,15,48,48),5,fill='#713b4b',outline='#9d6352',width=2)
                for x,y in ((14,16),(49,16),(14,50),(49,50)):
                    d.rectangle((x-2,y-2,x+2,y+2),fill='#d6af7c')
                cut = name=='receiver-cut'
                d.ellipse((21,21,43,43),fill='#443041' if cut else (210+pulse,66+pulse,59),outline='#f0ad7a',width=2)
                d.ellipse((27,27,37,37),fill=(121+pulse,90,82) if cut else '#fff2ba')
                if name == 'emitter':
                    # Emitter faces right. The renderer mirrors the east one.
                    d.rounded_rectangle((37,26,60,38),4,fill='#a37e62',outline='#f4c195',width=2)
                    d.rectangle((54,29,61,35),fill=(249,148+pulse,91))
            sheet.alpha_composite(im,(frame*size,row*size))
    sheet.save(OUT/'quarry-laser.png',optimize=True)
    meta = {'image':'quarry-laser.png','frameSize':size,'fps':12,'frames':count,
            'rows':{name:row for row,name in enumerate(rows)}}
    (OUT/'quarry-laser.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')


def make_map():
    def inside(x,y,areas):
        return any(l<=x<r and t<=y<b for l,t,r,b in areas)
    enemies = [(12.1,20.75,'earth','melee'),(25.2,20.6,'earth','ranged'),
               (29.55,5.6,'lightning','melee'),(33.56,11.5,'lightning','ranged')]
    data = {
        'id':'room-08', 'name':'절벽 운반로', 'columns':36, 'rows':25,
        'tileIds':dict(floor=0,crackedFloor=1,mossFloor=2,wall=3,pit=4,spikes=5),
        'tiles':[[3 if inside(x+.5,y+.5,COVER) else 0 if inside(x+.5,y+.5,FLOOR) else 4
                  for x in range(36)] for y in range(25)],
        'heroReferenceHeight':89, 'preview':{'playerSpeed':3.5,'meleeSpeed':2,'fallSeconds':.65},
        'playerSpawn':{'x':18,'y':23.7,'facing':'up'}, 'plannedExit':{'x':26,'y':1.85},
        'aggroTrigger':{'x':0,'y':0,'width':36,'height':23},
        'enemies':[{'id':f'{role}-{i}','x':x,'y':y,'element':element,'behaviorType':role,'facing':'down'}
                   for i,(x,y,element,role) in enumerate(enemies,1)],
        'referenceArt':{'image':'quarry-terrain.png','minimumScale':1.3,'pixelsPerTile':UNIT,
                        'originPixels':ORIGIN,'walkable':FLOOR,'cover':COVER,'coverPixels':[],
                        'doorPixels':[956,78,1028,154],'openCliffs':[BRIDGE],'shotsCrossAbyss':True},
        'vineGate':{'x':15,'y':18.0,'width':6,'height':.67,'burnDuration':.675},
        'earthBridge':BRIDGE,'bridgeAxis':'x','requiredBridge':True,
        'stonePuzzle':{'start':[9.5,10.5],'plate':[16.5,13.5],'reset':[18.94,16.15],
                       'gate':GATES[0],'gatePixels':box(GATES[0]),'centeredSlide':True},
        'quarry':{'gates':GATES,'lasers':LASERS,'lamps':LAMPS,
                  'navigationAnchors':[(18,16),(8,15),(25,16),(29,10),(26,2),(33,11)],
                  'laserWallSlots':WALL_SLOTS,
                  'wallCues':[(27.78,12.04,'right'),(29.12,9.08,'left')]},
        'layoutRevision':4,
    }
    (OUT/'room-08.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    terrain()
    make_laser_sheet()
    make_map()
