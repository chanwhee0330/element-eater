"""3번 방 화로의 석조 외장으로 9번 방 수차 스프라이트를 만든다."""
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from dungeon_terrain import tint


MAPS = Path(__file__).resolve().parents[1] / 'assets/maps'
FRAME_SIZE = (184, 128)
PIVOT = (129, 110)
OPENING_FRAMES = 8
FRAMES, COLUMNS, FPS = 10, 5, 15
OPENING = (
    (120, 192), (120, 82), (125, 74), (134, 65), (145, 58), (155, 54),
    (165, 54), (175, 58), (186, 65), (195, 74), (200, 82), (200, 192),
)


def rotor(draw, phase):
    front, rear = (153, 85), (165, 81)
    angles = [phase + i * math.tau / 6 for i in range(6)]

    def point(center, angle, radius):
        return (round(center[0] + radius * math.cos(angle)),
                round(center[1] + radius * math.sin(angle)))

    def ring(center, radius, color, width):
        x, y = center
        draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=color, width=width)

    ring(rear, 28, '#211b27', 6)
    ring(rear, 25, '#634449', 3)
    draw.line((130, 85, 196, 79), fill='#241c28', width=9)
    draw.line((130, 83, 196, 77), fill='#79524c', width=3)
    for angle in sorted(angles, key=math.sin):
        top = math.sin(angle) < .15
        inside = point(front, angle, 23)
        outer = point(front, angle + .18, 30)
        lip = point(rear, angle + .18, 30)
        draw.polygon((inside, point(rear, angle, 23), lip, outer),
                     fill='#976855' if top else '#5e4045', outline='#30222b')
        draw.line((outer, lip), fill='#c89772' if top else '#87615a', width=2)
        spoke = point(front, angle, 24)
        draw.line((front, spoke), fill='#3a2831', width=6)
        draw.line((front, spoke), fill='#9a6c55', width=2)
    ring(front, 28, '#2a202a', 6)
    ring(front, 26, '#956b55', 3)
    x, y = front
    draw.arc((x-25, y-25, x+25, y+25), 184, 295, fill='#cc9c75', width=2)
    for angle in angles:
        px, py = point(front, angle, 25)
        draw.ellipse((px-1, py-1, px+1, py+1), fill='#d4a57e')
    draw.ellipse((x-9, y-9, x+9, y+9), fill='#392733')
    draw.ellipse((x-6, y-6, x+6, y+6), fill='#94634f')
    draw.rectangle((x-4, y-5, x+3, y-2), fill='#d5a57c')


def brick_texture(color):
    atlas = Image.open(MAPS / 'isometric/masonry-atlas.png').convert('RGB')
    size = atlas.width // 2
    return tint(atlas.crop((size, 0, size*2, size)), color)


def passage_arch():
    original = Image.open(MAPS / 'room-03' / 'forge-arch.png').convert('RGBA')
    split, extension = 125, 46
    wide = Image.new('RGBA', (original.width, original.height+extension))
    wide.paste(original.crop((0, 0, original.width, split)))
    brick = brick_texture((173, 137, 160)).resize((80, extension), Image.Resampling.LANCZOS)
    for x in range(0, original.width, brick.width):
        wide.paste(brick, (x, split))
    rim = ImageDraw.Draw(wide)
    for x in (107, 200):
        rim.rectangle((x, split, x+12, split+extension-1), fill='#55394b')
        rim.line((x+2, split, x+2, split+extension-1), fill='#765469', width=2)
        for y in range(split+12, split+extension, 13):
            rim.line((x, y, x+12, y), fill='#392831', width=2)
    wide.paste(original.crop((0, split, original.width, original.height)), (0, split+extension))
    return wide


def door_texture(mask):
    brick = brick_texture((165, 140, 162))
    left, top, right, bottom = mask.getbbox()
    width, height = right-left, bottom-top
    texture = Image.new('RGBA', (width, height))
    middle = width//2
    for x, span in ((0, middle), (middle, width-middle)):
        texture.paste(brick.resize((span, height), Image.Resampling.LANCZOS), (x, 0))
    draw = ImageDraw.Draw(texture)
    draw.line((middle-1, 0, middle-1, height-1), fill='#2b1e2a', width=2)
    draw.line((middle, 0, middle, height-1), fill='#5f4451')
    return texture


def inside_door(prop, mask, texture, progress):
    left, top, _, _ = mask.getbbox()
    width, height = texture.size
    middle = width//2
    easing = progress*progress*(3-2*progress)
    left_shift = round(middle*easing)
    right_shift = round((width-middle)*easing)
    cover = Image.new('RGBA', prop.size)
    cover.paste(texture.crop((left_shift, 0, middle, height)), (left, top))
    cover.paste(texture.crop((middle, 0, width-right_shift, height)), (left+middle+right_shift, top))
    cover.putalpha(ImageChops.multiply(cover.getchannel('A'), mask))
    prop.alpha_composite(cover)


def make_frame(arch, mask, texture, cycle, opening, turning):
    bay = Image.new('RGBA', arch.size)
    draw = ImageDraw.Draw(bay)
    draw.rectangle((119, 52, 201, 119), fill='#1d1722')
    for y, stagger in ((65, 0), (81, 6), (99, 0)):
        draw.line((119, y, 201, y), fill='#372632', width=2)
        for x in range(131+stagger, 198, 20):
            draw.line((x, y, x, y+15), fill='#281d29')
    draw.polygon(((122, 110), (169, 101), (200, 108), (200, 117), (120, 117)),
                 fill='#24464f' if turning else '#2e222d')
    rotor(draw, cycle * math.tau / 6 + .18)
    if turning:
        draw.polygon(((121, 112), (145, 110), (180, 109), (200, 110),
                      (200, 117), (121, 117)), fill='#397585')
        for i in range(5):
            drift = (cycle + i/5) % 1
            x = round(198 - drift * 72)
            y = 111 + i % 4
            draw.line((x, y, x+5, y), fill='#9ad8d3' if i % 2 else '#66adaf', width=2)
        for i in range(3):
            travel = (cycle + i/3) % 1
            x = 172 + round(19 * travel)
            y = 109 - round(13 * math.sin(travel * math.pi))
            draw.ellipse((x-1, y-1, x+1, y+1), fill='#9ad8d3')
    prop = Image.composite(bay, arch, mask)
    if opening < 1:
        inside_door(prop, mask, texture, opening)
    if turning:
        accent = ImageDraw.Draw(prop)
        for left, right in ((85, 110), (209, 234)):
            accent.ellipse((left, 108, right, 120), fill='#223543')
            accent.line((left+3, 117, right-2, 117), fill='#457c87', width=3)
            x = left+5+round(cycle*12)
            accent.line((x, 114, x+4, 114), fill='#95d0cf', width=2)
    frame = Image.new('RGBA', FRAME_SIZE)
    frame.alpha_composite(prop.resize((FRAME_SIZE[0], PIVOT[1]), Image.Resampling.LANCZOS))
    return frame


def build():
    folder = MAPS / 'room-09'
    arch = passage_arch()
    mask = Image.new('L', arch.size)
    ImageDraw.Draw(mask).polygon(OPENING, fill=255)
    texture = door_texture(mask)
    width, height = FRAME_SIZE
    frames = OPENING_FRAMES + FRAMES + 1
    atlas = Image.new('RGBA', (width*COLUMNS, height*math.ceil(frames/COLUMNS)))
    for index in range(frames):
        row, col = divmod(index, COLUMNS)
        opening = min(1, index / (OPENING_FRAMES+1))
        cycle = max(0, index-1) % FRAMES / FRAMES
        frame = make_frame(arch, mask, texture, cycle, opening, index > 0)
        atlas.paste(frame, (col*width, row*height))
    name = 'trial-waterwheel'
    atlas.save(folder / f'{name}.png', optimize=True)
    metadata = {
        'image': f'{name}.png', 'frameSize': FRAME_SIZE, 'pivot': PIVOT,
        'openingFrames': OPENING_FRAMES, 'activeFrames': FRAMES,
        'columns': COLUMNS, 'fps': FPS, 'pixelsPerTile': 46,
    }
    (folder / f'{name}.json').write_text(
        json.dumps(metadata, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    build()
