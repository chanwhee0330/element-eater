"""PixelFX 체크아웃에서 7·8번 방 장치의 스프라이트를 다시 만든다."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / 'assets/maps'
VARIANTS = (
    ('garden', 'wheel', False), ('garden', 'wheel', True),
    ('garden', 'pump', False), ('garden', 'pump', True),
    ('garden', 'gate', False), ('garden', 'exit', False),
    ('quarry', 'wheel', False), ('quarry', 'gate', False), ('quarry', 'exit', False),
)


def frames(folder, name):
    metadata = json.loads((folder / f'{name}.json').read_text(encoding='utf-8'))
    with Image.open(folder / metadata['meta']['image']) as sheet:
        for entry in metadata['frames']:
            rect = entry['frame']
            x, y, w, h = (rect[key] for key in ('x', 'y', 'w', 'h'))
            yield sheet.crop((x, y, x+w, y+h)).convert('RGBA')


def build(checkout):
    effects = checkout / 'src/fx/element-eater'
    effects.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / 'assets/prompts/room-hardware-pixelfx.js', effects / '_hardware.js')
    names = {}
    for room, part, active in VARIANTS:
        name = f'{room}-{part}' + ('-active' if active else '')
        names[name] = room, part, active
        (effects / f'{name}.js').write_text(
            'import { hardware } from "./_hardware.js";\n'
            f'export const {{ meta, draw }} = hardware("{room}", "{part}", {str(active).lower()});\n',
            encoding='utf-8',
        )
    ids = [f'element-eater/{name}' for name in names]
    subprocess.run(['node', 'tools/render.mjs', *ids, '--sheet'], cwd=checkout, check=True)
    subprocess.run(['node', 'tools/check.mjs', *ids], cwd=checkout, check=True)
    garden = MAPS / 'room-07'
    atlas_path = garden / 'garden-objects.png'
    meta = json.loads((garden / 'garden-objects.json').read_text(encoding='utf-8'))
    with Image.open(atlas_path) as image:
        atlas = image.convert('RGBA')
    for name, (room, part, active) in names.items():
        tiles = list(frames(checkout / 'records/element-eater' / name, name))
        if room == 'garden' and part in ('wheel', 'pump'):
            row = meta['rows'][part + ('-active' if active else '')]
            width, height = meta['frameSize']
            for i in range(meta['frames']):
                atlas.paste(tiles[i % len(tiles)], (i*width, row*height))
        else:
            filename = {'wheel': 'reset-lever.png', 'gate': 'passage-gate.png', 'exit': 'exit-grille.png'}[part]
            folder = 'room-07' if room == 'garden' else 'room-08'
            tiles[0].save(MAPS / folder / filename, optimize=True)
    atlas.save(atlas_path, optimize=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    build(parser.parse_args().checkout.resolve())
