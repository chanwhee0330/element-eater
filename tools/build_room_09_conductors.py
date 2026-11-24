"""6번 방 전도체 원화에 문양을 새겨 9번 방 전도체 아틀라스를 만든다."""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance


MAPS = Path(__file__).resolve().parents[1] / 'assets/maps'
RUNES = {
    '△': ((33, 38), (42, 48), (24, 48)),
    '□': ((27, 38), (39, 38), (39, 48), (27, 48)),
    '◇': ((33, 38), (43, 43), (33, 48), (23, 43)),
}


def engrave(source, points, powered):
    body = source.copy()
    if not powered:
        body = ImageEnhance.Color(body).enhance(.72)
        body = ImageEnhance.Brightness(body).enhance(.78)
    draw = ImageDraw.Draw(body)
    draw.polygon(((20, 35), (46, 35), (51, 39), (51, 47),
                  (46, 51), (20, 51), (15, 47), (15, 39)), fill='#332536')
    draw.polygon(((21, 36), (45, 36), (50, 40), (50, 46),
                  (45, 50), (21, 50), (16, 46), (16, 40)), fill='#6c4d60')
    draw.polygon(((22, 37), (44, 37), (48, 40), (48, 46),
                  (44, 49), (22, 49), (18, 46), (18, 40)), fill='#483241')
    draw.line((22, 36, 44, 36), fill='#a67c84')
    for x in (19, 47):
        draw.point((x, 43), fill='#c59675')
        draw.point((x, 44), fill='#77525a')
    groove = (*points, points[0])
    draw.line(groove, fill='#251923', width=4, joint='curve')
    draw.line(groove, fill='#e1ab70' if powered else '#b9917c', width=2, joint='curve')
    return body


def build():
    folder = MAPS / 'room-09'
    room = json.loads((folder / 'room-09.json').read_text(encoding='utf-8'))
    symbols = room['trial']['runes']
    sources = [Image.open(MAPS / 'room-06' / f'conductor-{level}.png').convert('RGBA')
               for level in range(4)]
    width, height = sources[0].size
    atlas = Image.new('RGBA', (width*5, height*len(symbols)))
    for row, symbol in enumerate(symbols):
        for column, source in enumerate([sources[0], *sources]):
            cell = engrave(source, RUNES[symbol], powered=column > 0)
            atlas.paste(cell, (column*width, row*height))
    atlas.save(folder / 'trial-conductors.png', optimize=True)


if __name__ == '__main__':
    build()
