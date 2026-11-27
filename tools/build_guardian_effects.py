"""수호자 공격·변신의 뒤/앞 레이어를 공용 투명 아틀라스로 만든다."""

import json
import math
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw


FOLDER = Path(__file__).resolve().parents[1] / 'assets/sprites/boss/animation'
SIZE, COLUMNS, FRAMES, EVENT = 224, 18, 16, 7
PIVOT = (112, 184)
PALETTES = {
    'fire': ((122, 30, 64), (255, 100, 45), (255, 232, 149)),
    'wind': ((32, 105, 100), (111, 235, 184), (230, 255, 224)),
    'earth': ((121, 56, 48), (226, 155, 78), (255, 219, 156)),
    'lightning': ((83, 37, 152), (182, 94, 255), (248, 225, 255)),
    'water': ((30, 77, 158), (55, 196, 240), (212, 253, 255)),
}


def rgba(color, alpha):
    return (*color, round(255 * max(0, min(1, alpha))))


def orbit(x, y, rx, ry, angle):
    return x + rx * math.cos(angle), y + ry * math.sin(angle)


def arc(x, y, rx, ry, start, span, wobble=0):
    segments = max(6, math.ceil(abs(span) * 10))
    return [orbit(x, y, rx + wobble * math.sin(i * .8), ry,
                  start + span * i / segments) for i in range(segments + 1)]


def diamond(draw, x, y, radius, color, *, flat=1):
    draw.polygon(((x-radius, y), (x, y-radius*flat), (x+radius, y), (x, y+radius*flat)), fill=color)


def shine(draw, points, palette, power, width=2):
    dark, color, light = palette
    draw.line(points, fill=rgba(dark, .31 * power), width=width + 5, joint='curve')
    draw.line(points, fill=rgba(color, .73 * power), width=width + 2, joint='curve')
    draw.line(points, fill=rgba(light, power), width=width, joint='curve')


def floor_seal(draw, palette, frame, charge, burst, transform):
    x, y = PIVOT
    dark, color, light = palette
    radius = 43 + 18 * charge + (45 if transform else 32) * burst
    strength = min(.88, .16 + .47 * charge + .60 * burst)
    draw.ellipse((x-radius-6, y-radius*.26-4, x+radius+6, y+radius*.26+4),
                 fill=rgba(dark, strength * .23))
    for i in range(3):
        turn = i * math.tau / 3 + frame * .21
        shine(draw, arc(x, y, radius, radius * .24, turn, 1.43), palette, strength)
        draw.line(arc(x, y, radius-10, (radius-10)*.24, -turn, 1.1),
                  fill=rgba(color, strength * .77), width=2)
    for i in range(8):
        a = i * math.tau / 8 - frame * .042
        rx, ry = orbit(x, y, radius * .77, radius * .18, a)
        diamond(draw, rx, ry, 3 + burst * 1.5, rgba(light, strength), flat=.46)
    if burst:
        outline = radius + 11
        draw.line(arc(x, y, outline, outline * .23, 0, math.tau),
                  fill=rgba(color, strength * (1 - burst * .3)), width=2)


def element_strokes(draw, element, palette, frame, power, bloom, transform, back):
    dark, color, light = palette
    turn = frame * .24
    x, y = 112, 113
    spread = 26 * bloom
    if element == 'fire':
        for i, side in enumerate((-1, 1)):
            cx = x + side * (47 + spread*.65)
            base = y + (48 if back else 25) + 4 * math.sin(turn+i)
            points = [(cx-side*12, base), (cx+side*5, base-15),
                      (cx-side*5, base-33), (cx+side*7, base-47), (cx+side*2, base-61)]
            draw.polygon((*points, (cx-side*14, base-36), (cx-side*20, base-10)),
                         fill=rgba(color, power * .53))
            shine(draw, points, palette, power, 2)
    elif element == 'wind':
        for i in range(3):
            radius = 49+i*9+spread
            angle = turn+i*.9+(math.pi if back else 0)
            points = arc(x, y+20-i*10, radius, 19+i*4, angle, 1.7, 2)
            shine(draw, points, palette, power * (1-i*.16), 2)
            draw.line(arc(x, y+17-i*10, radius+5, 21+i*4, angle+.20, .94),
                      fill=rgba(color, power*.56), width=1)
    elif element == 'earth':
        for i in range(5):
            a = turn*.58+i*1.28+(0 if back else .62)
            px, py = orbit(x, y+21, 52+spread, 38+spread*.65, a)
            s = (5+i%3*2) * (1+bloom*.24)
            points = [(px-s, py), (px-s*.33, py-s*.88), (px+s*.71, py-s*.64),
                      (px+s, py+s*.13), (px+s*.23, py+s*.8), (px-s*.7, py+s*.56)]
            draw.polygon(points, fill=rgba(dark, power), outline=rgba(color, power))
            draw.polygon(points[:4], fill=rgba(color, power))
            draw.line(points[1:3], fill=rgba(light, power), width=2)
    elif element == 'lightning':
        random = Random(frame + (1 if back else 17))
        for i, side in enumerate((-1, 1, -1)):
            start_x = x + side * (43 + spread) + i*5
            points = [(start_x+random.randint(-9, 9), y-49+j*16+(0 if back else 16))
                      for j in range(6)]
            shine(draw, points, palette, power*(.76+i*.11), 2)
            px, py = points[2]
            shine(draw, [(px, py), (px+side*10, py+6), (px+side*21, py-4)], palette, power*.65, 1)
    else:
        for i in range(3):
            radius = 43+i*10+spread
            angle = turn*.64+i*1.7+(2 if back else 0)
            points = arc(x, y+29-i*8, radius, 16+i*7, angle, 1.39, 2)
            draw.line(points, fill=rgba(dark, power*.63), width=10-i)
            shine(draw, points, palette, power*(1-i*.13), 2)
            for px, py in points[::4]:
                draw.ellipse((px-2, py-3, px+2, py+1), fill=rgba(light, power*.85))
    if transform and back:
        for i in range(5):
            angle = i * math.tau / 5 + turn
            px, py = orbit(x, y+16, 56+spread, 27+spread*.45, angle)
            shine(draw, [(px, py+16), (px+2, py-12-bloom*22)], palette, power*.52, 1)


def motes(draw, palette, frame, charge, burst, transform):
    dark, color, light = palette
    phase = max(0, (frame - EVENT) / (FRAMES - 1 - EVENT))
    strength = .48 * charge + (1 - phase) * burst
    if not strength:
        return
    for i in range(23 if transform else 14):
        angle = i * 2.399 + frame * (.07 if burst else .18)
        radius = 39 + (i * 17 % 30) + (41 if transform else 27) * phase
        x, y = orbit(112, 113, radius, radius * .59, angle)
        y -= phase * (i % 4) * 9
        size = (2 + i % 4) * (.57 + .35 * burst)
        diamond(draw, x, y, size+1, rgba(dark, strength * .52))
        diamond(draw, x, y, size, rgba(color if i % 3 else light, strength))


def change_seal(draw, palette, frame, charge, burst, back):
    dark, color, light = palette
    x, y = 112, 107
    if charge and back:
        for i in range(5):
            a = frame * .16 + i * math.tau / 5
            px, py = orbit(x, y, 75 - 19 * charge, 48 - 13 * charge, a)
            diamond(draw, px, py, 8, rgba(dark, charge*.52))
            diamond(draw, px, py, 5.5, rgba(color, charge*.88))
            diamond(draw, px, py, 2.5, rgba(light, charge))
    if not burst:
        return
    if back:
        for i in range(10):
            angle = i * math.tau / 10 + .15
            inner = 40 + (1-burst)*37
            outer = 83 + (1-burst)*13 + i % 2 * 7
            origin = orbit(x, y, inner, inner*.82, angle)
            tip = orbit(x, y, outer, outer*.87, angle)
            side_a = orbit(x, y, inner+17, (inner+17)*.84, angle-.095)
            side_b = orbit(x, y, inner+17, (inner+17)*.84, angle+.095)
            draw.polygon((origin, side_a, tip, side_b), fill=rgba(color, burst*.66))
            draw.line((origin, tip), fill=rgba(light, burst*.79), width=1)
    else:
        radius = 60 + (1-burst)*36
        for i in range(2):
            angle = (i * math.pi) + .38 + (1-burst)*.70
            shine(draw, arc(x, y+10, radius, radius*.61, angle, 1.09),
                  palette, burst*.55, 2)
            px, py = orbit(x, y+10, radius, radius*.61, angle+1.09)
            diamond(draw, px, py, 5, rgba(light, burst*.93))


def render(element, kind, layer, frame):
    image = Image.new('RGBA', (SIZE, SIZE))
    draw = ImageDraw.Draw(image)
    palette = PALETTES[element]
    transform = kind == 'transform'
    charge = (frame / (EVENT - 1)) ** .82 if frame < EVENT else 0
    after = max(0, (frame - EVENT) / (FRAMES - 1 - EVENT))
    burst = (1 - after) ** 1.37 if frame >= EVENT else 0
    power = min(1, charge * (.84 if transform else .60) + burst)
    if not power:
        return image
    bloom = math.sin(min(1, after * 1.18) * math.pi * .5) if burst else 0
    back = layer == 'behind'
    if back:
        floor_seal(draw, palette, frame, charge, burst, transform)
    if transform:
        change_seal(draw, palette, frame, charge, burst, back)
    element_strokes(draw, element, palette, frame, power, bloom, transform, back)
    if not back:
        motes(draw, palette, frame, charge, burst, transform)
        if burst > .62:
            dark, color, light = palette
            radius = ((19 if transform else 12) * burst)
            diamond(draw, 112, 111, radius, rgba(dark, burst*.37), flat=1.65)
            diamond(draw, 112, 111, radius*.64, rgba(color, burst*.83), flat=1.65)
            diamond(draw, 112, 111, radius*.27, rgba(light, burst), flat=2.3)
    return image


def main():
    clips = {}
    for element in PALETTES:
        clips[element] = {}
        for kind in ('attack', 'transform'):
            clips[element][kind] = {}
    entries = [(element, kind, layer) for element in clips for kind in clips[element]
               for layer in ('behind', 'front')]
    rows = math.ceil(len(entries) * FRAMES / COLUMNS)
    sheet = Image.new('RGBA', (COLUMNS * SIZE, rows * SIZE))
    for index, (element, kind, layer) in enumerate(entries):
        first = index * FRAMES
        clips[element][kind][layer] = first
        for frame in range(FRAMES):
            row, col = divmod(first + frame, COLUMNS)
            sheet.paste(render(element, kind, layer, frame), (col * SIZE, row * SIZE))
    filename = 'guardian-cast-effects.png'
    sheet.save(FOLDER / filename, optimize=True)
    spec = {'image': filename, 'cell': SIZE, 'columns': COLUMNS, 'rows': rows,
            'pivot': PIVOT, 'scale': 1.58, 'count': FRAMES, 'event': EVENT, 'clips': clips}
    (FOLDER / 'guardian-cast-effects.json').write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
