"""7번 방 오브젝트를 게임 시간과 장치 상태에 맞춰 그린다."""
import json
import math


class GardenArt:
    def __init__(self, app, folder):
        self.app = app
        meta = json.loads((folder / 'garden-objects.json').read_text(encoding='utf-8'))
        self.sheet = app.p.load_image(str(folder / meta['image']))
        self.rows = meta['rows']
        self.fps = meta['fps']
        self.frames = meta['frames']
        self.width, self.height = meta['frameSize']

    @property
    def room(self):
        return self.app.room

    def sprite(self, kind, x, y, width, height, phase=0, frame=None):
        if frame is None:
            frame = int(self.room.elapsed * self.fps + phase) % self.frames
        left = frame * self.width
        bottom = self.sheet.h - (self.rows[kind] + 1) * self.height
        sx, sy = self.app.point(x, y)
        unit = self.app.view.tile_width
        width, height = width*unit, height*unit
        if (-width/2 <= sx <= self.app.width + width/2 and -height/2 <= sy <= self.app.height + height/2):
            self.sheet.clip_draw(left, bottom, self.width, self.height, sx, sy, width, height)

    def scenery(self, kind, bounds, phase):
        left, top, right, bottom = bounds
        self.sprite(kind, (left+right)/2, (top+bottom)/2, right-left, bottom-top, phase)

    def mechanism(self, key):
        room = self.room
        x, y = room.sluice[key]
        active = room.sluice_wheel if key == 'wheel' else room.sluice_pump
        kind = key + ('-active' if active else '')
        frame = None
        if key == 'wheel' and active:
            progress = room.garden_wheel_time / .5
            frame = min(self.frames - 1, round(progress * (self.frames - 1)))
        self.sprite(kind, x, y, 2.0, 1.55, frame=frame)
        distance = math.hypot(room.player.x-x, room.player.y-y)
        if distance < 3.35:
            sx, sy = self.app.point(x, y)
            self.app.ui.begin()
            if active:
                self.app.ui.text('잠금 해제' if key == 'wheel' else '전력 공급', sx, sy+36, 13)
            elif key == 'pump' or room.vine_open:
                self.app.ui.text('G · 손잡이' if key == 'wheel' else '번개 Space · 펌프', sx, sy+36, 13)

    def wires(self):
        app = self.app
        room = self.room
        app.ui.begin()
        for wire, active in zip(room.garden['wires'], (room.sluice_wheel, room.sluice_pump, room.sluice_ready)):
            if not active:
                continue
            distance = 0
            for start, end in zip(wire, wire[1:]):
                length = math.dist(start, end)
                for i in range(max(1, math.ceil(length/.24))):
                    offset = i * .24
                    if (distance + offset - room.elapsed * 7) % 1.65 < .52:
                        x = start[0] + (end[0] - start[0]) * offset / length
                        y = start[1] + (end[1] - start[1]) * offset / length
                        sx, sy = app.point(x, y)
                        app.p.draw_circle(sx, sy, 2, 255, 202, 101, filled=True)
                distance += length

    def gate(self, bounds, side=False):
        app = self.app
        room = self.room
        left, top, right, bottom = bounds
        progress = room.garden_gate_time / room.garden_gate_seconds
        progress = progress * progress * (3 - 2*progress)
        if side:
            app.ui.begin()
            segments = ((top, top + (bottom-top)/2 * (1-progress)),
                        (bottom - (bottom-top)/2 * (1-progress), bottom))
            for start, end in segments:
                if end - start < .03:
                    continue
                x0, y1 = app.point(left, start)
                x1, y0 = app.point(right, end)
                app.p.draw_rectangle(x0, y0, x1, y1, 46, 40, 47, filled=True)
                for i in range(math.ceil((end-start)/.27)):
                    _, y = app.point(left, start+i*.27)
                    app.p.draw_line(x0, y, x1, y, 172, 140, 94)
            for y in (top, bottom):
                x, sy = app.point((left+right)/2, y)
                app.p.draw_circle(x, sy, 4, 154, 131, 95, filled=True)
        else:
            image = app.gate_image
            visible = round(image.h * (1-progress))
            if visible:
                x, y = app.point((left+right)/2, top + (bottom-top)*visible/image.h/2)
                unit = app.view.tile_width
                image.clip_draw(0, 0, image.w, visible, x, y,
                                (right-left)*unit, (bottom-top)*unit*visible/image.h)
            app.ui.begin()
            x0, y = app.point(left, top)
            x1, _ = app.point(right, top)
            app.p.draw_line(x0, y, x1, y, 172, 144, 111)
        # Gold pulses make the locked doors legible even before either device is used.
        if not room.sluice_ready:
            x, y = app.point((left+right)/2, (top+bottom)/2)
            glow = round(18*math.sin(room.elapsed*4))
            app.p.draw_circle(x, y, 4, 222+glow, 151+glow, 80, filled=True)

    def exit(self, opening=None):
        app, room = self.app, self.room
        x0, y0, x1, y1 = room.reference_art['doorPixels']
        center = (x0+x1)/2
        app.ui.begin()
        if opening is None:
            opening = room.garden_exit_time / room.garden_exit_seconds
        if opening < 1:
            for offset in range(-24, 25, 8):
                top = y0 + 28 - math.sqrt(28**2 - offset**2)
                x, sy = app.view.reference_point(center+offset, top)
                _, end = app.view.reference_point(center+offset, y1-(y1-top)*opening)
                app.p.draw_line(x, sy, x, end, 175, 142, 99)
        else:
            entry = room.data['plannedExit']
            app.view.draw_exit_marker(entry['x'], entry['y'], True)
        x, y = app.view.reference_point(center, y0+27)
        glow = round(22*math.sin(room.elapsed*4))
        color = (144+glow, 228+glow, 175) if room.exit_open else (204+glow, 166+glow, 100)
        app.ui.diamond(x, y, 7, color)

    def layers(self):
        room = self.room
        for kind, bounds in (('planter', room.garden['planters']), ('pool', room.garden['pools']),
                             ('fountain', [room.garden['fountain']])):
            for index, rect in enumerate(bounds):
                yield rect[3], self.scenery, (kind, rect, index*3)
        for i, (x, y) in enumerate(room.garden['lamps']):
            active = (room.sluice_wheel, room.sluice_pump, True, True, room.exit_open, room.exit_open)[i]
            yield y, self.sprite, ('lamp-active' if active else 'lamp', x, y-.23, .68, .85, i*2)
        for key in ('wheel', 'pump'):
            yield room.sluice[key][1], self.mechanism, (key,)
        yield room.sluice['gate'][3], self.gate, (room.sluice['gate'],)
        for bounds in room.sluice['returnGates']:
            yield bounds[3], self.gate, (bounds, True)
