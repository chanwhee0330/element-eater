"""7번 방 오브젝트를 게임 시간과 장치 상태에 맞춰 그린다."""
import json
import math


class GardenArt:
    def __init__(self, app, folder):
        self.app = app
        meta = json.loads((folder / 'garden-objects.json').read_text(encoding='utf-8'))
        self.passage_gate = app.p.load_image(str(folder / 'passage-gate.png'))
        self.exit_grille = app.p.load_image(str(folder / 'exit-grille.png'))
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

    def slide_gate(self, image, bounds, opening):
        left, top, right, bottom = bounds
        vertical = bottom-top > right-left
        start, end = (top, bottom) if vertical else (left, right)
        axis = (left+right)/2 if vertical else (top+bottom)/2
        depth = right-left if vertical else bottom-top
        visible = round(image.w/2 * (1-opening))
        if visible <= 0:
            return
        unit = self.app.view.tile_width
        span = (end-start)*visible/image.w
        for offset, center in ((0, start+span/2), (image.w-visible, end-span/2)):
            x, y = self.app.point(axis, center) if vertical else self.app.point(center, axis)
            angle = -math.pi/2 if vertical else 0
            image.clip_composite_draw(offset, 0, visible, image.h, angle, '',
                                      x, y, span*unit, depth*unit)

    def gate(self, bounds):
        left, top, right, bottom = bounds
        progress = self.room.garden_gate_time / self.room.garden_gate_seconds
        opening = progress * progress * (3 - 2*progress)
        image = self.passage_gate
        if bottom-top > right-left:
            self.slide_gate(image, bounds, opening)
            return
        visible = round(image.h * (1-opening))
        if visible > 0:
            depth = (bottom-top)*visible/image.h
            x, y = self.app.point((left+right)/2, top+depth/2)
            unit = self.app.view.tile_width
            image.clip_draw(0, 0, image.w, visible, x, y, (right-left)*unit, depth*unit)

    def exit(self, opening=None, image=None):
        app, room = self.app, self.room
        x0, y0, x1, y1 = room.reference_art['doorPixels']
        center = (x0+x1)/2
        if opening is None:
            opening = room.garden_exit_time / room.garden_exit_seconds
        if image is None:
            image = self.exit_grille
        visible = round(image.h * (1-opening))
        if visible > 0:
            height = (y1-y0)*visible/image.h
            x, y = app.view.reference_point(center, y0+height/2)
            scale = app.view.reference_scale
            image.clip_draw(0, 0, image.w, visible, x, y, (x1-x0)*scale, height*scale)
        else:
            entry = room.data['plannedExit']
            app.view.draw_exit_marker(entry['x'], entry['y'], True)
        app.ui.begin()
        x, y = app.view.reference_point(center, y0+9)
        glow = round(22*math.sin(room.elapsed*4))
        color = (144+glow, 228+glow, 175) if room.exit_open else (204+glow, 166+glow, 100)
        app.ui.diamond(x, y, 4, color)

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
            yield bounds[3], self.gate, (bounds,)
