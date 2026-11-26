"""9번 방과 같은 석재 아틀라스로 오원 제단의 바닥과 소환 장치를 만든다."""

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from dungeon_terrain import DungeonTerrain


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / 'assets/maps'
OUT = MAPS / 'room-10'
UNIT, ORIGIN = 30, (290, 142)
FLOOR = [(13,1,17,4), (9,3,21,5), (6,5,24,7), (3,7,27,17), (1,10,3,14),
         (27,10,29,14), (6,17,24,19), (9,19,21,21), (13,21,17,24)]
COVER = [(6,8.6,8.5,9.25), (21.5,8.6,24,9.25), (6.7,14.7,9,15.35), (21,14.7,23.3,15.35)]
CENTER = (15,11.25)
DEVICES = [(12.45,14.86), (10.88,10.05), (15,6.15), (19.12,10.05), (17.55,14.86)]
GLYPHS = (
    [[(0,-8),(-6,1),(-6,5),(0,8),(6,5),(6,1),(0,-8)]],
    [[(-6,6),(-8,1),(-4,-6),(-1,-2),(2,-10),(8,0),(6,6),(-6,6)], [(-2,4),(1,0),(4,4)]],
    [[(-9,-3),(5,-3),(8,-5),(7,-8),(2,-8)], [(-10,1),(7,1),(10,4),(7,7),(3,7)], [(-6,5),(-1,5)]],
    [[(-8,6),(-5,-4),(0,-8),(7,-3),(9,6),(-8,6)], [(-5,-4),(1,0),(7,-3)], [(1,0),(1,6)]],
    [[(3,-9),(-7,1),(-1,1),(-3,9),(7,-2),(0,-2),(3,-9)]],
)


def export_terrain():
    art = DungeonTerrain(UNIT, ORIGIN, FLOOR, 1010, (23,13,17), (1,13,17))
    art.rug(14.05,18,15.95,24)
    art.rug(14.15,1,15.85,5)
    d = art.draw
    cx,cy = art.point(*CENTER)
    for radius,color,width in ((136,'#453340',10),(132,'#866254',2),(128,'#bb8c60',3),
                               (124,'#6c4a49',3),(117,'#927469',2),(99,'#503b43',8),
                               (97,'#b38560',2),(91,'#927162',2),(87,'#5a434d',2)):
        d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=color,width=width)
    for angle in range(0,360,9):
        a = math.radians(angle)
        points = [(round(cx+r*math.cos(a)),round(cy+r*math.sin(a))) for r in (103,113)]
        d.line(points,fill='#594149',width=3)
        d.line([(x+1,y) for x,y in points],fill='#ad846a')
    feeds = []
    for i, ((tx,ty), glyph) in enumerate(zip(DEVICES,GLYPHS)):
        x,y = art.point(tx,ty)
        dx,dy = tx-CENTER[0],ty-CENTER[1]
        length = math.hypot(dx,dy)
        tip = tuple(round(CENTER[j]+(dx,dy)[j]*4.25/length,4) for j in (0,1))
        join = art.point(*tip)
        d.line((join,(x,y)),fill='#45343f',width=6)
        d.line((join,(x,y)),fill='#9f765f',width=2)
        feeds.append(tip)
        diamond = [(x,y-19),(x+23,y),(x,y+19),(x-23,y)]
        d.polygon([(u,v+2) for u,v in diamond],fill='#41323b')
        d.polygon(diamond,fill='#625256',outline='#aa9484',width=2)
        for path in glyph:
            d.line([(x+a,y+b+1) for a,b in path],fill='#392c37',width=4,joint='curve')
            d.line([(x+a,y+b) for a,b in path],fill='#ae9b88',width=2,joint='curve')
    for gx,gy in ((9.6,3.32),(20.4,3.32),(6.45,5.35),(23.55,5.35),
                  (1.35,10.35),(28.65,10.35),(9.4,19.25),(20.6,19.25),(13.13,21.36),(16.87,21.36)):
        x,y=art.point(gx,gy)
        d.rectangle((x-8,y-2,x+8,y+5),fill='#45303f',outline='#281e2c')
        d.line((x-8,y-3,x+8,y-3),fill='#bb8a63',width=2)
        d.polygon([(x-6,y-4),(x-6,y-11),(x-1,y-17),(x+1,y-11),(x+5,y-21),(x+7,y-8),(x+5,y-4)],
                  fill='#e58349')
        d.polygon([(x-3,y-4),(x-2,y-12),(x+1,y-8),(x+4,y-14),(x+5,y-4)],fill='#ffdc9b')
    art.image.save(OUT/'guardian-terrain.png',optimize=True)
    data = {
        'id':'room-10', 'name':'오원 제단', 'columns':30, 'rows':24,
        'tileIds':dict(floor=0,crackedFloor=1,mossFloor=2,wall=3,pit=4,spikes=5),
        'tiles':[[0 if (x,y) in art.cells else 4 for x in range(30)] for y in range(24)],
        'heroReferenceHeight':89, 'preview':dict(playerSpeed=3.5, meleeSpeed=2,fallSeconds=.65),
        'playerSpawn':dict(x=15,y=22.5,facing='up'), 'plannedExit':dict(x=15,y=1.42),
        'aggroTrigger':dict(x=3,y=5,width=24,height=14),
        'enemies':[dict(id='guardian-1',x=CENTER[0],y=CENTER[1],element='fire',behaviorType='melee',facing='down')],
        'referenceArt':dict(image='guardian-terrain.png',minimumScale=1.15,pixelsPerTile=UNIT,
                            originPixels=ORIGIN,walkable=FLOOR,cover=COVER,coverPixels=[],
                            wallOpenings=[(24,13,17),(1,13,17)],walledBoundary=True),
        'layoutRevision':2,
        'boss':dict(hp=450,formSeconds=8.0,center=CENTER,devices=DEVICES,feeds=feeds,
                    windStartY=7.5,windPlateY=6.15,arena=(5,4.5,25,17.6),
                    exitGate=(13,2.05,17,2.55),exitOpening=(14.32,15.68)),
    }
    (OUT/'room-10.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def export_objects():
    def image(path):
        return Image.open(MAPS/path).convert('RGBA')

    sources = {}
    garden = image('room-07/garden-objects.png')
    dry = garden.crop((0,96,128,192))
    # 꺼진 수반의 물 픽셀만 눌러 돌 테두리는 유지한다.
    pixels = dry.load()
    for y in range(96):
        for x in range(128):
            r,g,b,a = pixels[x,y]
            if a and g > 1.17*r and b > 1.18*r:
                pixels[x,y] = (42,34,45,a)
    sources['basin'] = [dry, *(garden.crop((x*128,96,(x+1)*128,192)) for x in range(12))]
    flame = Image.open(ROOT/'assets/effects/temple-preview/fire/brazier/brazier.png').convert('RGBA')
    cold = Image.new('RGBA',(112,148))
    brazier = ImageDraw.Draw(cold)
    for foot in (42,54,69):
        brazier.line((56,114,foot,143),fill='#3d2e39',width=5)
        brazier.line((56,114,foot,137),fill='#806349',width=2)
    brazier.polygon(((35,107),(77,107),(70,118),(42,118)),fill='#73503f',outline='#3b2b34',width=2)
    brazier.ellipse((32,99,80,112),fill='#2c222a',outline='#a48360',width=3)
    brazier.arc((34,101,78,113),8,172,fill='#cf9f70',width=2)
    sources['fire'] = [cold, *(flame.crop((x*112,0,(x+1)*112,148)) for x in range(11))]
    coil = image('room-09/trial-conductors.png')
    sources['coil'] = [coil.crop((x*66,0,(x+1)*66,67)) for x in range(5)]
    entries = {}
    sheet = Image.new('RGBA',(128*13,160*len(sources)))
    for row,(key,frames) in enumerate(sources.items()):
        cut = []
        for column,frame in enumerate(frames):
            x,y = column*128,row*160
            sheet.paste(frame,(x,y))
            cut.append((x,sheet.height-y-frame.height,frame.width,frame.height))
        entries[key] = cut
    sheet.save(OUT/'guardian-objects.png',optimize=True)
    (OUT/'guardian-objects.json').write_text(json.dumps(entries,indent=2)+'\n',encoding='utf-8')

    body = Image.open(ROOT/'assets/sprites/boss/guardian-fire-idle.png').convert('RGBA')
    output = Image.new('RGBA',(256*5,256))
    for y in range(256):
        for x in range(256):
            r,g,b,a = body.getpixel((x,y))
            if not a:
                continue
            if r > 135 and g > 1.15*b and (120 < y < 182 or 81 < y < 108):
                r,g,b = int(r*.66),int(g*.62),int(b*.82)
            cut = 81-(y//15)
            part = 0 if x<cut else 1 if x>256-cut else 2 if y<110 else 4 if y>195 else 3
            output.putpixel((part*256+x,y),(r,g,b,a))
    output.save(OUT/'guardian-assembly.png',optimize=True)


if __name__ == '__main__':
    export_terrain()
    export_objects()
