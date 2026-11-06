"""고정 원화와 움직이는 원화를 분리하여 맵 대기 동작을 베이크한다.

아트 레이어는 image_gen으로 제작한다. 여기서는 같은 본체 복사, 레이어 합성,
고정 피벗 회전과 프레임 내보내기만 수행하며 프레임별 본체 재생성을 하지 않는다.
"""
from pathlib import Path
import json
from PIL import Image, ImageChops, ImageDraw, ImageFilter


def solid_bounds(image, alpha=96):
    return image.getchannel('A').point(lambda value: 255 if value >= alpha else 0).getbbox()


def fit_ground(image, width, height, pivot=(64, 114), size=128):
    bounds = solid_bounds(image)
    trim = (max(0, bounds[0] - 3), max(0, bounds[1] - 3), min(image.width, bounds[2] + 3), min(image.height, bounds[3] + 3))
    cropped = image.crop(trim)
    scale = min(width / (bounds[2] - bounds[0]), height / (bounds[3] - bounds[1]))
    result = cropped.resize((round(cropped.width * scale), round(cropped.height * scale)), Image.Resampling.LANCZOS)
    frame = Image.new('RGBA', (size, size))
    anchor = ((bounds[0] + bounds[2]) / 2 - trim[0], bounds[3] - trim[1])
    frame.alpha_composite(result, (round(pivot[0] - anchor[0] * scale), round(pivot[1] - anchor[1] * scale)))
    return frame


def grid_cells(image):
    for row in range(2):
        for col in range(4):
            yield image.crop((round(col * image.width / 4), round(row * image.height / 2), round((col + 1) * image.width / 4), round((row + 1) * image.height / 2)))


def binary_alpha(image):
    return image.getchannel('A').point(lambda value: 255 if value else 0)


def copy_protected(frame, body, mask):
    # Binary copy also preserves the same RGBA values on anti-aliased edge pixels.
    frame.paste(body, (0, 0), mask)
    return frame


def bake_layers(source, size=128):
    folder = Path(source) / 'layers'
    cfg = json.loads((folder / 'layer-recipe.json').read_text(encoding='utf-8'))
    load = lambda name: Image.open(folder / name).convert('RGBA')
    exports = {}

    def save(name, frames, fixed_mask, body, details):
        strip = Image.new('RGBA', (size * len(frames), size))
        for index, frame in enumerate(frames):
            strip.alpha_composite(frame, (index * size, 0))
            # Compare every protected pixel, including RGB values in soft alpha edges.
            for channel in ImageChops.difference(frame, body).split():
                assert ImageChops.multiply(channel, fixed_mask).getbbox() is None, (name, index, 'fixed pixels changed')
        strip.save(folder / f'{name}-baked.png')
        fixed_mask.save(folder / f'{name}-fixed-mask.png')
        body.save(folder / f'{name}-fixed-body.png')
        exports[name] = {'frames': frames, 'source': folder / f'{name}-baked.png',
                         'details': {**details, 'fixedMask': f'source/layers/{name}-fixed-mask.png',
                                     'fixedBody': f'source/layers/{name}-fixed-body.png', 'fixedPixelsVerified': True}}

    # A single jar bitmap is reused; all changes are clipped to the exposed water.
    body = load('water-body.png')
    water = cfg['water']
    clip = Image.new('L', (size, size))
    ImageDraw.Draw(clip).ellipse(water['waterClip'], fill=255)
    fixed = ImageChops.multiply(binary_alpha(body), ImageChops.invert(clip))
    frames = []
    for raw in grid_cells(load('water-ripples-source.png')):
        layer = Image.new('RGBA', (size, size))
        box = water['effectBox']
        raw = raw.resize((box[2] - box[0], box[3] - box[1]), Image.Resampling.LANCZOS)
        layer.alpha_composite(raw, (box[0], box[1]))
        layer.putalpha(ImageChops.multiply(layer.getchannel('A'), clip))
        frames.append(copy_protected(Image.alpha_composite(body, layer), body, fixed))
    save('water', frames, fixed, body, {'method': 'static-jar-plus-water-ripples', 'waterClip': water['waterClip']})

    # A fixed log bundle supports the flame; the flame is drawn on its upper face.
    logs = cfg['fire']
    body = fit_ground(load('fire-logs-source.png'), logs['width'], logs['height'])
    flame_cells = list(grid_cells(load('fire-flames-source.png')))
    flame_bounds = [solid_bounds(image) for image in flame_cells]
    scale = min(logs['flameMaxWidth'] / max(b[2] - b[0] for b in flame_bounds), logs['flameMaxHeight'] / max(b[3] - b[1] for b in flame_bounds))
    flame_layers = []
    for cell in flame_cells:
        # Cell origin is fixed; no re-centering from a changing flame silhouette.
        target = cell.resize((round(cell.width * scale), round(cell.height * scale)), Image.Resampling.LANCZOS)
        frame = Image.new('RGBA', (size, size))
        frame.alpha_composite(target, (round(64 - target.width / 2), round(logs['flameBaseY'] - target.height * .85)))
        flame_layers.append(frame)
    moving = Image.new('L', (size, size))
    for layer in flame_layers:
        moving = ImageChops.lighter(moving, binary_alpha(layer))
    fixed = ImageChops.multiply(binary_alpha(body), ImageChops.invert(moving))
    frames = [copy_protected(Image.alpha_composite(body, layer), body, fixed) for layer in flame_layers]
    save('fire', frames, fixed, body, {'method': 'flame-on-top-of-static-logs', 'flameBasePixelsTopLeft': [64, logs['flameBaseY']], 'drawOrder': ['logs', 'flame']})

    # Only the center bolt's brightness and exterior sparks animate, with fixed geometry.
    body = load('lightning-body.png')
    lightning = cfg['lightning']
    off = fit_ground(load('lightning-off-source.png'), lightning['offWidth'], lightning['offHeight'])
    off.putalpha(body.getchannel('A'))
    bolt_mask = Image.new('L', (size, size))
    x0, y0, x1, y1 = lightning['boltRegion']
    for y in range(y0, y1):
        for x in range(x0, x1):
            red, green, blue, alpha = body.getpixel((x, y))
            if alpha > 180 and red > 175 and green > 120 and red > blue * 1.5 and green > blue * 1.7:
                bolt_mask.putpixel((x, y), 255)
    bolt_mask = bolt_mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.45))
    bolt_mask.save(folder / 'lightning-bolt-mask.png')
    fixed = ImageChops.multiply(binary_alpha(body), ImageChops.invert(bolt_mask.point(lambda value: 255 if value else 0)))
    frames = []
    for index, cell in enumerate(grid_cells(load('lightning-sparks-source.png'))):
        frame = Image.new('RGBA', (size, size))
        frame.alpha_composite(cell.resize((size - 8, size - 8), Image.Resampling.LANCZOS), (4, 4))
        frame.putalpha(ImageChops.multiply(frame.getchannel('A'), ImageChops.invert(binary_alpha(body))))
        state = Image.composite(Image.blend(off, body, lightning['boltPulse'][index]), body, bolt_mask)
        state.putalpha(body.getchannel('A'))
        frame = Image.alpha_composite(frame, state)
        frames.append(copy_protected(frame, body, fixed))
    save('lightning', frames, fixed, body, {'method': 'static-battery-bolt-pulse-and-exterior-sparks', 'boltMask': 'source/layers/lightning-bolt-mask.png', 'boltPulse': lightning['boltPulse']})

    # Only the front-left small rock moves. The rear and right rocks use one fixed image.
    earth = cfg['earth']
    body = fit_ground(load('earth-fixed-rocks-source.png'), earth['fixedWidth'], earth['fixedHeight'], pivot=tuple(earth['fixedPivot']))
    factor = 4
    small = fit_ground(load('earth-small-rock-source.png'), earth['smallWidth'] * factor, earth['smallHeight'] * factor,
                       pivot=tuple(value * factor for value in earth['smallGround']), size=size * factor)
    center = tuple(value * factor for value in earth['smallRotationCenter'])
    moving = Image.new('L', (size, size))
    layers = []
    for lift, degrees in earth['motion']:
        rotated = small.rotate(degrees, resample=Image.Resampling.BICUBIC, center=center)
        layer = Image.new('RGBA', (size * factor, size * factor))
        layer.alpha_composite(rotated, (0, round(lift * factor)))
        layer = layer.resize((size, size), Image.Resampling.LANCZOS)
        layers.append(layer)
        moving = ImageChops.lighter(moving, binary_alpha(layer))
    fixed = ImageChops.multiply(binary_alpha(body), ImageChops.invert(moving))
    frames = [copy_protected(Image.alpha_composite(body, layer), body, fixed) for layer in layers]
    moving.save(folder / 'earth-moving-mask.png')
    save('earth', frames, fixed, body, {'method': 'fixed-rear-and-right-rocks-moving-front-left-rock', 'movingMask': 'source/layers/earth-moving-mask.png', 'smallRockMotion': earth['motion']})

    # One rotor, one stand and one hub; only the rotor's angle changes.
    wind = cfg['wind']
    factor = 4
    axis = tuple(wind['axis'])
    stand = fit_ground(load('wind-stand-source.png'), wind['standWidth'], wind['standHeight'])
    rotor_source = load('wind-rotor-source.png')
    raw_axis = wind['sourceAxis']
    scale = wind['rotorScale']
    rotor = rotor_source.resize((round(rotor_source.width * scale * factor), round(rotor_source.height * scale * factor)), Image.Resampling.LANCZOS)
    unrotated = Image.new('RGBA', (size * factor, size * factor))
    unrotated.alpha_composite(rotor, (round((axis[0] - raw_axis[0] * scale) * factor), round((axis[1] - raw_axis[1] * scale) * factor)))
    radius = wind['hubRadius']
    hub_mask = Image.new('L', (size, size))
    ImageDraw.Draw(hub_mask).ellipse((axis[0] - radius, axis[1] - radius, axis[0] + radius - 1, axis[1] + radius - 1), fill=255)
    hub = unrotated.resize((size, size), Image.Resampling.LANCZOS)
    fixed_body = stand.copy()
    fixed_body.paste(hub, (0, 0), hub_mask)
    fixed = Image.new('L', (size, size))
    # Lower stand remains visible below every possible rotor angle.
    fixed.paste(binary_alpha(stand).crop((0, wind['protectedStandY'], size, size)), (0, wind['protectedStandY']))
    fixed = ImageChops.lighter(fixed, hub_mask)
    frames = []
    for index in range(wind['frameCount']):
        moving = unrotated.rotate(-index * 360 / wind['frameCount'], resample=Image.Resampling.BICUBIC, center=(axis[0] * factor, axis[1] * factor)).resize((size, size), Image.Resampling.LANCZOS)
        frame = Image.alpha_composite(stand, moving)
        frames.append(copy_protected(frame, fixed_body, fixed))
    save('wind', frames, fixed, fixed_body, {'method': 'rigid-rotor-fixed-axis', 'rotationCenterPixelsTopLeft': list(axis), 'degreesPerFrame': 360 / wind['frameCount'], 'protectedStandFromY': wind['protectedStandY']})
    return exports
