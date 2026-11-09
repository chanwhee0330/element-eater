"""생성된 투명 배경 장식을 지도 배경에 배치한다. 충돌/타일 데이터는 수정하지 않는다."""
import json
from PIL import Image, ImageChops


def apply_decorations(background, grid, unit, source):
    settings = json.loads((source / 'decorations.json').read_text(encoding='utf-8'))
    atlas = Image.open(source / settings['atlas']).convert('RGBA')
    cols, rows = settings['atlasGrid']['columns'], settings['atlasGrid']['rows']
    decals = {}
    for name, slot in settings['slots'].items():
        x, y = slot % cols, slot // cols
        cell = atlas.crop((round(x*atlas.width/cols), round(y*atlas.height/rows),
                           round((x+1)*atlas.width/cols), round((y+1)*atlas.height/rows)))
        # 투명 여백의 1~2 알파 노이즈가 장식의 표시 크기를 줄이지 않게 등록한다.
        bounds = cell.getchannel('A').point(lambda a: 255 if a >= 32 else 0).getbbox()
        assert bounds, name
        bounds = (max(0, bounds[0]-4), max(0, bounds[1]-4), min(cell.width, bounds[2]+4), min(cell.height, bounds[3]+4))
        decals[name] = cell.crop(bounds)
    # 실제 바닥의 안쪽에만 배치한다. 절벽 실루엣·가시·벽 판독성을 보존한다.
    floor = Image.new('L', background.size, 0)
    for y, row in enumerate(grid):
        for x, tile in enumerate(row):
            if tile < 3:
                floor.paste(255, (x*unit+5, y*unit+5, (x+1)*unit-5, (y+1)*unit-5))
    # 타일 사이 줄눈에서도 자연스럽게 이어지되 위험 경계에는 접근하지 않게 한다.
    from PIL import ImageFilter
    floor = floor.filter(ImageFilter.MaxFilter(11)).filter(ImageFilter.MinFilter(7))
    result = background.convert('RGBA')
    layer = Image.new('RGBA', background.size)
    for item in settings['placements']:
        decal = decals[item['kind']]
        width = round(item['width']*unit)
        height = round(width*decal.height/decal.width)
        decal = decal.resize((width, height), Image.Resampling.LANCZOS)
        if item.get('flip'):
            decal = decal.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if item.get('rotation', 0):
            decal = decal.rotate(item['rotation'], Image.Resampling.BICUBIC, expand=True)
        opacity = item.get('opacity', 1)
        if opacity != 1:
            decal.putalpha(decal.getchannel('A').point(lambda a: round(a*opacity)))
        at = round(item['x']*unit-decal.width/2), round(item['y']*unit-decal.height/2)
        layer.alpha_composite(decal, at)
    layer.putalpha(ImageChops.multiply(layer.getchannel('A'), floor))
    result.alpha_composite(layer)
    return result.convert('RGB')
