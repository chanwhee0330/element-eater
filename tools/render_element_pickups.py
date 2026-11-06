"""원소 시트로 비교 GIF/PNG 및 같은 프레임을 재생하는 오프라인 HTML을 만든다."""
from pathlib import Path
import base64
import io
import json
import math
import runpy
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/items/elements'
OUT = ROOT / 'outputs/previews/element-pickups'
FONT = Path('C:/Windows/Fonts/malgun.ttf')


def font(size):
    return ImageFont.truetype(str(FONT), size) if FONT.exists() else ImageFont.load_default(size=size)


def as_data(image):
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii')


def frame_index(element, time):
    return math.floor(max(0, time) * element['fps'] + 1e-9) % element['frameCount']


def render():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = json.loads((ASSETS / 'element-pickups.json').read_text(encoding='utf-8'))
    placement = json.loads((ROOT / 'assets/maps/obstacle-room/source/element-pickup-view.json').read_text(encoding='utf-8'))
    scene = runpy.run_path(str(ROOT / 'tools/render_ingame_preview.py'))
    atlas = Image.open(ASSETS / catalog['image']).convert('RGBA')
    size = catalog['frameSize']['w']
    pivot = catalog['pivotPixelsTopLeft']
    unit = scene['screen_unit']
    drawables = []
    for item in placement['placements']:
        el = catalog['elements'][item['element']]
        ground = item['ground']
        gx, gy = ground['x'], ground['y']
        assert 0 <= gx < scene['data']['columns'] and 0 <= gy < scene['data']['rows']
        assert scene['data']['tiles'][int(gy)][int(gx)] in (0, 1, 2), f'unsafe pickup: {item}'
        sx, sy = (gx - scene['left']) * unit, (gy - scene['top']) * unit
        scale = unit * el['heightUnits'] / el['referenceSolidHeightPixels']
        w = h = round(size * scale)
        at = (round(sx - pivot['x'] * scale), round(sy - pivot['y'] * scale))
        # Keep all art inside the camera and above the bottom HUD.
        assert at[0] >= 0 and at[1] >= 112 and at[0] + w < scene['W'] and sy < 600
        frames = [atlas.crop((i * size, el['atlasRow'] * size, (i + 1) * size, (el['atlasRow'] + 1) * size)).resize((w, h), Image.Resampling.LANCZOS) for i in range(el['frameCount'])]
        drawables.append({'element': item['element'], 'el': el, 'frames': frames, 'at': at,
                          'groundX': sx, 'groundY': sy, 'scale': scale, 'phase': item['phaseSeconds']})
    hero_size = scene['source_size']
    hero_frames = [scene['sheet'].crop((i * hero_size, scene['row'] * hero_size, (i + 1) * hero_size, (scene['row'] + 1) * hero_size)).resize(scene['sprite'].size, Image.Resampling.LANCZOS) for i in range(8)]
    hero = {'element': 'hero', 'frames': hero_frames, 'at': scene['at'], 'groundX': scene['px'], 'groundY': scene['foot_y'], 'scale': scene['scale'], 'phase': 0, 'el': {'fps': 4, 'frameCount': 8}}
    ordered = sorted(drawables + [hero], key=lambda item: item['groundY'])
    shadow = Image.new('RGBA', scene['background'].size)
    d = ImageDraw.Draw(shadow)
    for item in ordered:
        x, y = item['groundX'], item['groundY']
        radius = 25 if item is hero else min(29, unit * item['el']['heightUnits'] * 0.28)
        d.ellipse((x - radius, y - 6, x + radius, y + 4), fill=(26, 27, 20, 75))
    base = Image.alpha_composite(scene['background'], shadow)

    def map_frame(t):
        image = base.copy()
        for item in ordered:
            image.alpha_composite(item['frames'][frame_index(item['el'], t + item['phase'])], item['at'])
        return Image.alpha_composite(image, scene['ui']).convert('RGB')

    # Same five sources at a larger inspection size, no changes to their color or alpha.
    def gallery_frame(t):
        image = Image.new('RGBA', (1280, 350), '#14251e')
        d = ImageDraw.Draw(image)
        d.text((30, 18), '맵 원소 · 대기 애니메이션', fill='#f3edd4', font=font(22))
        for index, (name, el) in enumerate(catalog['elements'].items()):
            x = 20 + index * 252
            d.rounded_rectangle((x, 58, x + 232, 330), radius=16, fill='#23382d', outline='#526746')
            d.text((x + 116, 83), f'{el["name"]} · {el["object"]}', anchor='mm', fill='#f3edd4', font=font(21))
            d.text((x + 116, 303), f'{el["frameCount"]}프레임 · {el["fps"]}fps', anchor='mm', fill='#b4c7a5', font=font(15))
            frame = frame_index(el, t)
            art = atlas.crop((frame * size, el['atlasRow'] * size, (frame + 1) * size, (el['atlasRow'] + 1) * size)).resize((184, 184), Image.Resampling.LANCZOS)
            image.alpha_composite(art, (x + 24, 98))
        return image.convert('RGB')

    map_frame(0).save(OUT / 'element-pickups-map.png')
    gallery_frame(0).save(OUT / 'element-pickups-designs.png')
    frames = [map_frame(index / 20) for index in range(80)]
    # Shared palette prevents a stationary map from shimmering due to per-frame quantization.
    sampler = Image.new('RGB', (320, 180 * 8))
    for index in range(8):
        sampler.paste(frames[index * 10].resize((320, 180)), (0, index * 180))
    palette = sampler.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in frames]
    quantized[0].save(OUT / 'element-pickups-map.gif', save_all=True, append_images=quantized[1:], duration=50, loop=0, optimize=False, disposal=1)
    gallery = [gallery_frame(index / 20) for index in range(80)]
    gp = gallery[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    gallery = [image.quantize(palette=gp, dither=Image.Dither.NONE) for image in gallery]
    gallery[0].save(OUT / 'element-pickups-animation.gif', save_all=True, append_images=gallery[1:], duration=50, loop=0, optimize=False, disposal=1)
    (OUT / 'element-pickups-fixed-animation.gif').write_bytes((OUT / 'element-pickups-animation.gif').read_bytes())
    (OUT / 'element-pickups-refined-animation.gif').write_bytes((OUT / 'element-pickups-animation.gif').read_bytes())

    payload = {'atlas': as_data(atlas), 'background': as_data(scene['background']), 'hud': as_data(scene['ui']),
               'hero': as_data(scene['sheet']), 'catalog': catalog,
               'heroDraw': {'at': list(hero['at']), 'size': list(hero['frames'][0].size),
                            'groundX': hero['groundX'], 'groundY': hero['groundY'], 'row': scene['row'], 'frameSize': hero_size},
               'items': [{key: item[key] for key in ('element', 'at', 'groundX', 'groundY', 'scale', 'phase')} for item in drawables]}
    template = (ROOT / 'tools/element_pickups_preview.html').read_text(encoding='utf-8')
    script = (ROOT / 'tools/element_pickups_preview.js').read_text(encoding='utf-8')
    (OUT / 'element-pickups-preview.html').write_text(template.replace('__PAYLOAD__', json.dumps(payload, ensure_ascii=False)).replace('__SCRIPT__', script), encoding='utf-8')
    print(f'Rendered 5 pickups on safe floor, camera {scene["view_w"]}x{scene["view_h"]}, 80 frames / 4 seconds.')
    print(OUT)


if __name__ == '__main__':
    render()
