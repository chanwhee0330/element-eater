"""수호자 옆·후면 원화에서 방향별 동작과 피격 마스크를 만든다."""

import base64
import json
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


FOLDER = Path(__file__).resolve().parents[1] / 'assets/sprites/boss/animation'
FORMS = ('fire', 'wind', 'earth', 'lightning', 'water')
SIZE, CELL, FRAME_COUNT = 320, 8, 12
PIVOT = {'x': 160, 'y': 264}
COLUMNS = 12
ROWS = 12
ACTION_FRAMES = 6
# 초당 1.65칸, 칸당 36.8px, 반 주기 0.6초의 지면 이동량.
CONTACT_DISTANCE = 1.65 * 36.8 * .6
# 공격별 몸 낮춤, 전진 기울기, 팔 뻗기, 팔 들기, 강조색.
ATTACK = {
    'fire': (9, 13, 18, 9, (255, 135, 52)),
    'wind': (15, 23, 11, 3, (183, 255, 212)),
    'earth': (17, 4, 6, 22, (250, 188, 113)),
    'lightning': (5, 8, 14, 18, (225, 155, 255)),
    'water': (10, 4, 18, 12, (117, 234, 255)),
}


def register(source, column, row, front_bounds, *, rows, rear=False):
    tile = source.crop((source.width * column // 5, source.height * row // rows,
                        source.width * (column + 1) // 5, source.height * (row + 1) // rows))
    alpha = tile.getchannel('A')
    left, top, right, bottom = alpha.point(lambda value: 255 if value >= 96 else 0).getbbox()
    front_left, front_top, front_right, front_bottom = front_bounds
    scale_y = (front_bottom - front_top) / (bottom - top)
    scale_x = (front_right - front_left) / (right - left) if rear else scale_y
    # 원화 칸 가장자리의 미세한 잡티를 제외하고 실루엣 주변 여백만 남긴다.
    crop_x, crop_y = max(0, left - 4), max(0, top - 4)
    tile = tile.crop((crop_x, crop_y, min(tile.width, right + 4), min(tile.height, bottom + 3)))
    tile = tile.resize((round(tile.width * scale_x), round(tile.height * scale_y)), Image.Resampling.LANCZOS)
    tile.putalpha(tile.getchannel('A').point(lambda value: value if value >= 48 else 0))
    registered = Image.new('RGBA', (SIZE, SIZE))
    registered.paste(tile, (round(PIVOT['x'] - ((left + right) / 2 - crop_x) * scale_x),
                            round(PIVOT['y'] - (bottom - crop_y) * scale_y)))
    return registered


def walk_parts(pose, hip, direction):
    alpha = pose.getchannel('A')
    selection = Image.new('L', pose.size)
    upper_edge = 118 if direction == 'up' else 110
    lower_edge = 106 if direction == 'up' else 99
    ImageDraw.Draw(selection).polygon(
        ((upper_edge, hip), (159, hip), (159, 274), (70, 274), (78, 247),
         (lower_edge, 235), (upper_edge - 4, 225)),
        fill=255,
    )
    upper_alpha = alpha
    legs = []
    for mask in (selection, ImageOps.mirror(selection)):
        leg_alpha = ImageChops.multiply(alpha, mask)
        leg = pose.copy()
        leg.putalpha(leg_alpha)
        if direction == 'up':
            # 기존 덧댄 골반판 대신 바로 아래 허벅지 갑옷을 이음새까지 연결한다.
            thigh = leg.crop((0, 232, SIZE, 245))
            joint = hip - 17
            leg.paste(thigh.resize((SIZE, 245 - joint), Image.Resampling.BICUBIC), (0, joint))
        legs.append(leg)
        upper_alpha = ImageChops.subtract(upper_alpha, leg_alpha)
    # 다리 원래 위치에 고정되어 남는 갑옷 가장자리와 옆으로 뻗은 골반판을 걷기에서 정리한다.
    draw_upper = ImageDraw.Draw(upper_alpha)
    if direction in ('left', 'right'):
        draw_upper.rectangle((79, hip + 6, 240, 274), fill=0)
        draw_upper.rectangle((201, hip, 222, hip + 6), fill=0)
    elif direction == 'up':
        taper = ((108, hip - 13), (133, hip - 14), (146, hip - 5),
                 (145, hip + 19), (93, hip + 36), (93, hip + 8))
        draw_upper.polygon(taper, fill=0)
        draw_upper.polygon([(SIZE - 1 - x, y) for x, y in taper], fill=0)
        draw_upper.rectangle((87, hip + 12, 145, 274), fill=0)
        draw_upper.rectangle((174, hip + 12, 232, 274), fill=0)
    else:
        draw_upper.rectangle((94, hip + 18, 119, 274), fill=0)
        draw_upper.rectangle((200, hip + 18, 225, 274), fill=0)
    torso = pose.copy()
    torso.putalpha(upper_alpha)
    return torso, legs


def move_leg(leg, hip, stride, vertical):
    ankle = 248
    moved_ankle = ankle + vertical

    def sample(x, y):
        # 발목 아래는 모양을 유지한 채 평행 이동하고 위쪽 다리만 관절에 연결한다.
        progress = max(0, min(1, (y - hip) / (moved_ankle - hip)))
        return x - stride * progress, y - vertical * progress

    return deform(leg, sample)


def footstep(phase):
    if phase < .5:
        # 디딘 발은 본체가 전진한 거리만큼 몸 기준으로 일정하게 뒤로 간다.
        return CONTACT_DISTANCE * (.5 - 2 * phase), 0
    swing = 2 * phase - 1
    return CONTACT_DISTANCE * (smooth(swing) - .5), math.sin(math.pi * swing)


def walk_frame(parts, index, hip, direction, rear_heel=None):
    torso, legs = parts
    phase = index / FRAME_COUNT
    side = direction in ('right', 'left')
    swing = math.sin(phase * math.tau)
    stride_sign = -1 if direction == 'up' else 1
    frame = Image.new('RGBA', torso.size)
    # 두 다리를 반 주기 어긋나게 움직이고 카메라에 가까운 다리를 마지막에 그린다.
    for leg_index in (1, 0):
        sign = 1 if leg_index == 0 else -1
        travel, raised = footstep((phase + leg_index * .5) % 1)
        stride = 35 * sign + travel if side else 2 * swing * sign
        depth = -6 * leg_index if side else stride_sign * travel
        vertical = depth - (18 if side else 12) * raised
        leg = legs[leg_index]
        if rear_heel is not None and raised > .5:
            # 멀어지는 발걸음의 뒤쪽 발에는 새 원화의 밑창이 드러난다.
            heel = rear_heel if leg_index == 0 else ImageOps.mirror(rear_heel)
            leg = leg.copy()
            heel_box = (0, 236, SIZE, SIZE)
            leg.paste(Image.blend(leg.crop(heel_box), heel.crop(heel_box), smooth(2 * raised - 1)), (0, 236))
        frame.alpha_composite(move_leg(leg, hip, stride, vertical))

    def sample(x, y):
        core = max(0, min(1, (hip - y) / 34))
        arm = math.exp(-((y - 172) / 34)**2) * min(1, abs(x - 160) / 72)
        side_sign = -1 if x < 160 else 1
        return (x - 7 * arm * side_sign * swing * core,
                y + (3 * swing * swing + 4 * arm * side_sign * swing) * core)

    frame.alpha_composite(deform(torso, sample))
    # 망 변형 뒤 하체에 남는 한두 픽셀 폭의 조각을 걷기 프레임에서만 정리한다.
    alpha = frame.getchannel('A')
    box = (78, hip - 2, 242, 294)
    lower = alpha.crop(box)
    cleaned = lower.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    alpha.paste(ImageChops.darker(lower, cleaned), box[:2])
    frame.putalpha(alpha)
    return frame


def deform(pose, sample):
    mesh = []
    for y in range(0, SIZE, CELL):
        for x in range(0, SIZE, CELL):
            u, v = x + CELL, y + CELL
            corners = (sample(x, y), sample(x, v), sample(u, v), sample(u, y))
            mesh.append(((x, y, u, v), tuple(value for point in corners for value in point)))
    return pose.transform(pose.size, Image.Transform.MESH, mesh, Image.Resampling.BICUBIC)


def smooth(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def action_frame(pose, state, index, count, side, hip, element, release_frame):
    crouch, lean, reach, raise_arm, color = ATTACK[element]
    progress = index / (count - 1)
    if state == 'attack':
        anticipation = smooth(index / (release_frame - 1)) if index < release_frame else 0
        thrust = 0 if index < release_frame else 1 - smooth((index - release_frame) / (count - release_frame - 1))
        dip = crouch * (anticipation - .24 * thrust)
        tilt = lean * (thrust - .45 * anticipation)
        extension = reach * (thrust - .45 * anticipation)
        arm_lift = raise_arm * (.35 * anticipation + .75 * thrust)
        accent = .12 * anticipation + .19 * thrust
    else:
        charge = smooth(progress) if state == 'transform' else (1 - smooth(progress))
        dip = 10 * charge if state == 'transform' else -8 * charge
        tilt = 2 * math.sin(progress * math.tau * 2) * charge
        extension = -9 * charge
        arm_lift = 11 * charge
        accent = .32 * charge

    if not any((dip, tilt, extension, arm_lift, accent)):
        return pose

    def sample(x, y):
        # 공격과 변신은 두 발을 디딘 자세에서 상체만 움직인다.
        upper = max(0, min(1, (hip - y) / 34))
        fist_x = 243 if side else (81 if x < 160 else 239)
        arm = math.exp(-((x-fist_x)/47)**2 - ((y-185)/49)**2)
        outward = 1 if side or x >= 160 else -1
        dx = ((tilt if side else 0) + outward * extension * arm) * upper
        dy = (dip - arm_lift * arm) * upper
        return x - dx, y - dy

    frame = deform(pose, sample)
    upper = frame.crop((0, 0, SIZE, hip))
    rgb = Image.blend(upper.convert('RGB'), Image.new('RGB', upper.size, color), accent)
    rgb.putalpha(upper.getchannel('A'))
    frame.paste(rgb, (0, 0))
    fixed = hip + CELL
    frame.paste(pose.crop((0, fixed, SIZE, SIZE)), (0, fixed))
    return frame


def hit_mask(frame):
    alpha = frame.getchannel('A')
    side = SIZE // CELL
    bits = bytearray(side * side // 8)
    for row in range(side):
        for col in range(side):
            if alpha.getpixel((col * CELL + CELL // 2, row * CELL + CELL // 2)) >= 192:
                bit = row * side + col
                bits[bit // 8] |= 1 << (bit % 8)
    return base64.b64encode(bits).decode('ascii')


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def main():
    planted = Image.open(FOLDER / 'guardian-direction-planted.png').convert('RGBA')
    rear = Image.open(FOLDER / 'guardian-direction-rear.png').convert('RGBA')
    all_masks = {}
    for column, element in enumerate(FORMS):
        front_path = FOLDER / f'guardian-{element}-animations'
        front = Image.open(front_path.with_suffix('.png')).convert('RGBA').crop((0, 0, SIZE, SIZE))
        front_spec = json.loads(front_path.with_suffix('.json').read_text(encoding='utf-8'))
        attack_meta = front_spec['clips']['attack']
        release_frame = next(event['frame'] for event in attack_meta['events'] if event['name'] == 'release')
        timings = {state: [front_spec['frames'][key]['duration'] for key in front_spec['clips'][state]['frames']]
                   for state in ('attack', 'transform')}
        timings.update(idle=[100], walk=[100] * FRAME_COUNT, arrive=[110] * ACTION_FRAMES)
        timings['transform'] = timings['transform'][:ACTION_FRAMES]
        alpha = front.getchannel('A')
        bounds = alpha.point(lambda value: 255 if value >= 96 else 0).getbbox()
        right = register(planted, column, 0, bounds, rows=1)
        back = register(rear, column, 0, bounds, rows=2, rear=True)
        back_step = register(rear, column, 1, bounds, rows=2, rear=True)
        rear_heel = walk_parts(back_step, 212, 'up')[1][0]
        atlas = Image.new('RGBA', (SIZE * COLUMNS, SIZE * ROWS))
        image_name = f'guardian-{element}-walk.png'
        spec = {'schema': 'element-eater.sprite-atlas.v1', 'image': image_name,
                'element': element, 'imageSize': dict(width=atlas.width, height=atlas.height),
                'frameSize': dict(width=SIZE, height=SIZE), 'pivotPixelsTopLeft': PIVOT,
                'layout': dict(columns=COLUMNS, rows=ROWS), 'clips': {}, 'frames': {}}
        masks = all_masks[element] = {}
        slot = 0
        for direction in ('right', 'left', 'up', 'down'):
            side = direction in ('right', 'left')
            base, hip = (right, 206) if side else (back, 212) if direction == 'up' else (front, 220)
            parts = walk_parts(base, hip, direction)
            states = timings.items() if direction != 'down' else (('walk', timings['walk']),)
            for state, durations in states:
                clip_key = state if direction == 'down' else f'{state}_{direction}'
                clip = spec['clips'][clip_key] = dict(frames=[], loop=state in ('idle', 'walk'))
                if state == 'attack':
                    clip['events'] = attack_meta['events']
                hittable = state in ('idle', 'walk', 'attack')
                if hittable:
                    masks[clip_key] = []
                for index, duration in enumerate(durations):
                    if state == 'idle':
                        frame = base
                    elif state == 'walk':
                        frame = walk_frame(parts, index, hip, direction, rear_heel if direction == 'up' else None)
                    else:
                        frame = action_frame(base, state, index, len(durations), side, hip, element, release_frame)
                    if direction == 'left':
                        frame = ImageOps.mirror(frame)
                    x, y = slot % COLUMNS * SIZE, slot // COLUMNS * SIZE
                    atlas.paste(frame, (x, y))
                    slot += 1
                    key = f'{clip_key}_{index}'
                    clip['frames'].append(key)
                    spec['frames'][key] = {
                        'duration': duration, 'pivotPixelsTopLeft': PIVOT,
                        'pico2dClip': dict(left=x, bottom=atlas.height-y-SIZE, width=SIZE, height=SIZE),
                    }
                    if hittable:
                        masks[clip_key].append(hit_mask(frame))
        atlas.save(FOLDER / image_name, optimize=True)
        write_json(FOLDER / f'guardian-{element}-walk.json', spec)
    write_json(FOLDER / 'guardian-walk-hit-masks.json', all_masks)


if __name__ == '__main__':
    main()
