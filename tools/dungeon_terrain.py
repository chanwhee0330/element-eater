"""1~6번 방의 석재 아틀라스와 절벽 배경으로 레퍼런스 지형을 그린다."""
from pathlib import Path
from random import Random

from PIL import Image, ImageChops, ImageDraw


ASSETS = Path(__file__).resolve().parents[1] / 'assets/maps'
RESAMPLE = Image.Resampling.LANCZOS


def tint(image, color):
    return ImageChops.multiply(image, Image.new('RGB', image.size, color))


class DungeonTerrain:
    ledge_top_inset = 7
    rim_face_height = 17

    def __init__(self, unit, origin, regions, seed, entry, exit_span, *, open_banks=()):
        self.unit, self.origin = unit, origin
        self.cells = {(x, y) for l, t, r, b in regions for x in range(l, r) for y in range(t, b)}
        atlas = Image.open(ASSETS / 'isometric/masonry-atlas.png').convert('RGB')
        s = atlas.width // 2
        floor, brick, cap, self.runner = (
            atlas.crop((x*s, y*s, (x+1)*s, (y+1)*s))
            for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))
        )
        self.cap = tint(cap, (151, 176, 238))
        self.brick = tint(brick, (136, 148, 191))
        self.ledge_cap = tint(cap, (68, 115, 112))
        self.ledge_brick = tint(brick, (65, 101, 101))
        self.image = tint(Image.open(ASSETS / 'room-01/room-01-backdrop.png')
                          .convert('RGB').resize((1440, 940), RESAMPLE), (103, 92, 136))
        self.draw = ImageDraw.Draw(self.image)
        rng = Random(seed)
        cliff = tint(brick, (145, 122, 149)).resize((unit, 82), RESAMPLE)
        fade = Image.linear_gradient('L').resize(cliff.size).point(lambda value: 255-value)
        cells = sorted(self.cells, key=lambda xy: xy[::-1])
        for x, y in cells:
            if (x, y+1) not in self.cells:
                self.image.paste(cliff, self.point(x, y+1), fade)
        floors = [
            Image.blend(tint(floor.rotate(90*i), (v, v-3, v-21)), Image.new('RGB', floor.size, (197,157,127)), .16)
            .resize((unit, unit), RESAMPLE)
            for i in range(4) for v in (231, 239, 246, 253)
        ]
        for x, y in cells:
            self.image.paste(rng.choice(floors), self.point(x, y))
        self.entry, self.exit_span, self.open_banks = entry, exit_span, open_banks

    def point(self, x, y):
        ox, oy = self.origin
        return round(ox+x*self.unit), round(oy+y*self.unit)

    def rug(self, left, top, right, bottom):
        x, y = self.point(left, top)
        width = self.point(right, top)[0]-x
        area = tint(self.runner, (213, 203, 228)).resize((width, self.unit), RESAMPLE)
        for row in range(top, bottom):
            self.image.paste(area, (x, y+(row-top)*self.unit))

    def ledge(self, x, y, width, depth):
        y += self.ledge_top_inset
        face_height = 9 - self.ledge_top_inset
        self.image.paste(self.ledge_brick.resize((width, depth + face_height), RESAMPLE), (x, y))
        self.image.paste(self.ledge_cap.resize((width, depth), RESAMPLE), (x, y))
        self.draw.line((x, y, x+width-1, y), fill='#a9dec7')
        self.draw.line((x, y+depth-1, x+width-1, y+depth-1), fill='#24494c')

    def stone_wall(self, x, y, width, depth, face_height):
        self.image.paste(self.brick.resize((width, depth + face_height), RESAMPLE), (x, y))
        self.image.paste(self.cap.resize((width, depth), RESAMPLE), (x, y))
        self.draw.line((x, y+depth-1, x+width-1, y+depth-1), fill='#706585')

    def rims(self):
        entry_bottom, entry_start, entry_end = self.entry
        door_y, door_start, door_end = self.exit_span
        for x, y in sorted(self.cells, key=lambda xy: xy[::-1]):
            px, py = self.point(x, y)
            if (x, y-1) not in self.cells and not (y == door_y and door_start <= x < door_end):
                self.stone_wall(px, py - 22, self.unit, 8, self.rim_face_height)
            if (x, y+1) not in self.cells and not (y == entry_bottom and entry_start <= x < entry_end):
                self.stone_wall(px, py + self.unit - 15, self.unit, 7, self.rim_face_height)
            for side in (-1, 1):
                edge = x if side < 0 else x+1
                if (edge, y) in self.open_banks or (x+side, y) in self.cells:
                    continue
                self.stone_wall(px - 3 if side < 0 else px + self.unit - 3,
                                py - 8, 6, self.unit, 8)

    def door(self, bounds, wall_span):
        l, t, r, b = bounds
        left, right = wall_span
        for x in range(left, right, self.unit):
            width = min(self.unit, right-x)
            self.image.paste(self.brick.resize((width, b-t+18), RESAMPLE), (x, t-18))
            self.image.paste(self.cap.resize((width, 7), RESAMPLE), (x, t-21))
        self.draw.rounded_rectangle((l-5,t-4,r+5,b+1), radius=31, fill='#716382', outline='#938198', width=2)
        self.draw.rounded_rectangle((l,t,r,b), radius=28, fill='#19151e')
        self.draw.rectangle((l+1,b-24,r-1,b-1),fill='#19151e')
        for x in (l-17, r+17):
            self.draw.line((x-5,b-25,x+5,b-25),fill='#604250',width=3)
            for dx, dy in ((-4,0),(0,-3),(4,0)):
                self.draw.line((x+dx,b-25,x+dx,b-33+dy),fill='#d9a873',width=2)
                self.draw.point((x+dx,b-34+dy),fill='#ffe1a0')
