"""고정 본체와 움직이는 레이어를 합성하고 원소 PNG/JSON을 패킹한다."""
from pathlib import Path
import hashlib
import json
from PIL import Image
from bake_pickup_layers import bake_layers

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/items/elements'
SOURCE = ASSETS / 'source'


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def build():
    cfg = json.loads((SOURCE / 'recipe.json').read_text(encoding='utf-8'))
    size = cfg['frameSize']
    pivot = cfg['pivotPixelsTopLeft']
    columns, rows = cfg['sourceGrid']['columns'], cfg['sourceGrid']['rows']
    count = columns * rows
    layered = bake_layers(SOURCE, size)
    max_count = max(len(layered[e['id']]['frames']) if e['id'] in layered else count for e in cfg['elements'])
    combined = Image.new('RGBA', (size * max_count, size * len(cfg['elements'])))
    catalog = {'schema': 'element-eater.pickup-atlas.v1', 'image': 'element-pickups.png',
               'size': {'w': combined.width, 'h': combined.height}, 'frameSize': {'w': size, 'h': size},
               'pivotPixelsTopLeft': pivot, 'coordinateOrigin': 'top-left', 'loop': True,
               'elements': {}, 'frames': {},
               'generator': 'python tools/build_element_pickups.py',
               'status': '맵 대기 애니메이션 에셋과 시각 미리보기. 실제 섭취·전투와 별도.'}
    for row, element in enumerate(cfg['elements']):
        name = element['id']
        prepared = layered.get(name)
        sequence_count = len(prepared['frames']) if prepared else count
        source_path = SOURCE / f'{name}-idle-source.png'
        raw = Image.open(source_path).convert('RGBA')
        cells = []
        for index in range(count):
            col, source_row = index % columns, index // columns
            rect = (round(col * raw.width / columns), round(source_row * raw.height / rows),
                    round((col + 1) * raw.width / columns), round((source_row + 1) * raw.height / rows))
            cell = raw.crop(rect)
            solid = cell.getchannel('A').point(lambda a: 255 if a >= cfg['solidAlpha'] else 0)
            bounds = solid.getbbox()
            if bounds is None:
                raise ValueError(f'{name} frame {index}: empty source cell')
            # Lower structural part determines the anchor, independently of moving flame tips/arcs.
            base_top = round(bounds[1] + (bounds[3] - bounds[1]) * 0.63)
            base = solid.crop((0, base_top, cell.width, cell.height)).getbbox()
            anchor = ((base[0] + base[2]) / 2, base[3] + base_top)
            margin = cfg['trimMargin']
            trim = (max(0, bounds[0] - margin), max(0, bounds[1] - margin),
                    min(cell.width, bounds[2] + margin), min(cell.height, bounds[3] + margin))
            cells.append({'image': cell.crop(trim), 'anchor': (anchor[0] - trim[0], anchor[1] - trim[1]),
                          'cell': rect, 'trim': trim, 'bounds': bounds})
        # One uniform scale per sequence prevents frame-by-frame height normalization from pumping.
        art_width = max(c['bounds'][2] - c['bounds'][0] for c in cells)
        art_height = max(c['bounds'][3] - c['bounds'][1] for c in cells)
        scale = min(cfg['maxArtSize']['width'] / art_width, cfg['maxArtSize']['height'] / art_height)
        strip = Image.new('RGBA', (size * sequence_count, size))
        frames = {}
        solid_heights = []
        for index in range(sequence_count):
            cell = cells[index % count]
            image = cell['image']
            image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
            dx, dy = round(pivot['x'] - cell['anchor'][0] * scale), round(pivot['y'] - cell['anchor'][1] * scale)
            frame = Image.new('RGBA', (size, size))
            frame.alpha_composite(image, (dx, dy))
            if prepared:
                frame = prepared['frames'][index]
            bounds = frame.getchannel('A').point(lambda a: 255 if a >= cfg['solidAlpha'] else 0).getbbox()
            assert bounds and 2 <= bounds[0] < bounds[2] <= size - 2 and 2 <= bounds[1] < bounds[3] <= size - 2, (name, index, bounds)
            solid_heights.append(bounds[3] - bounds[1])
            strip.alpha_composite(frame, (index * size, 0))
            combined.alpha_composite(frame, (index * size, row * size))
            frame_name = f'{name}_idle_{index:02d}'
            frames[frame_name] = {'frame': {'x': index * size, 'y': 0, 'w': size, 'h': size},
                                  'duration': 1000 / element['fps'], 'rotated': False, 'trimmed': False,
                                  'spriteSourceSize': {'x': 0, 'y': 0, 'w': size, 'h': size},
                                  'sourceSize': {'w': size, 'h': size}, 'pivotPixelsTopLeft': pivot,
                                  'sourceCell': list(cell['cell']), 'solidBounds': list(bounds)}
            catalog['frames'][frame_name] = {**frames[frame_name], 'frame': {'x': index * size, 'y': row * size, 'w': size, 'h': size}}
        image_name = f'{name}-idle.png'
        strip.save(ASSETS / image_name)
        meta = {'image': image_name, 'size': {'w': strip.width, 'h': strip.height}, 'scale': '1',
                'frameTags': [{'name': 'idle', 'from': 0, 'to': sequence_count - 1, 'direction': 'forward'}],
                'animation': {'fps': element['fps'], 'frameCount': sequence_count, 'loop': True,
                              'seconds': sequence_count / element['fps'], 'pivotPixelsTopLeft': pivot},
                'source': f'source/{name}-idle-source.png', 'sourceGrid': cfg['sourceGrid'],
                'sourceSha256': hashlib.sha256(source_path.read_bytes()).hexdigest(), 'packingScale': scale}
        if prepared:
            meta.update({'source': prepared['source'].relative_to(ASSETS).as_posix(),
                         'sourceGrid': {'columns': sequence_count, 'rows': 1},
                         'sourceSha256': hashlib.sha256(prepared['source'].read_bytes()).hexdigest(),
                         'packingScale': 1.0, 'layeredAnimation': prepared['details']})
            for index, info in enumerate(frames.values()):
                info['sourceCell'] = [index * size, 0, (index + 1) * size, size]
                catalog['frames'][f'{name}_idle_{index:02d}']['sourceCell'] = info['sourceCell']
        write_json(ASSETS / f'{name}-idle.json', {'frames': frames, 'meta': meta})
        catalog['elements'][name] = {**element, 'animation': 'idle', 'frameCount': sequence_count,
                                     'atlasRow': row, 'image': image_name, 'data': f'{name}-idle.json',
                                     'referenceSolidHeightPixels': max(solid_heights),
                                     'frameNames': list(frames)}
        print(f'{name}: {sequence_count} frames, {element["fps"]}fps, {strip.width}x{strip.height}, reference height {max(solid_heights)}px')
    combined.save(ASSETS / catalog['image'])
    write_json(ASSETS / 'element-pickups.json', catalog)


if __name__ == '__main__':
    build()
