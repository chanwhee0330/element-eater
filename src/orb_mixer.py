"""오원 혼합기에 구슬을 드래그해서 넣는 화면."""
import math

from .boss import COLORS, RITUAL
from .elements import NAMES
from .learning_scene import smoothstep


class OrbMixer:
    socket_radius = 26
    activation_duration = .92

    def __init__(self, app):
        self.app = app
        self.center = (app.width / 2, app.height / 2)
        x, y = self.center
        self.mixing_center = (x, y + 46)
        self.sockets = {}
        for index, element in enumerate(RITUAL):
            angle = math.pi/2 - index*math.tau/len(RITUAL)
            self.sockets[element] = (x+77*math.cos(angle), y+46+77*math.sin(angle))
        self.slots = {element: (x + (i - 2) * 83, y - 102)
                      for i, element in enumerate(RITUAL)}
        self.dragging = None
        self.cursor = self.center
        self.elapsed = 0
        self.receipts = {}
        self.activation_started = None

    @property
    def ready(self):
        return (self.app.room.guardian.reward_loaded
                and (self.activation_started is None
                     or self.elapsed - self.activation_started >= self.activation_duration))

    def handle(self, event):
        app, p = self.app, self.app.p
        if event.type == p.SDL_KEYDOWN:
            if event.key == p.SDLK_ESCAPE:
                app.orb_mixer = None
            elif event.key == p.SDLK_f and self.ready:
                app.room.use_final_reward({'ingest'})
                app.orb_mixer = None
                app.save_progress()
        elif event.type in (p.SDL_MOUSEMOTION, p.SDL_MOUSEBUTTONDOWN, p.SDL_MOUSEBUTTONUP):
            self.cursor = (event.x, app.height - event.y)
            if event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_LEFT:
                for element, point in self.slots.items():
                    if app.room.inventory[element] and math.dist(point, self.cursor) <= 32:
                        self.dragging = element
                        break
            elif event.type == p.SDL_MOUSEBUTTONUP and event.button == p.SDL_BUTTON_LEFT:
                if (self.dragging and math.dist(self.cursor, self.sockets[self.dragging]) <= self.socket_radius
                        and app.room.insert_final_orb(self.dragging)):
                    self.receipts[self.dragging] = (self.elapsed, self.cursor)
                    if app.room.guardian.reward_loaded:
                        self.activation_started = self.elapsed
                    sound = app.sounds.get(f'switch-{self.dragging}')
                    if sound:
                        sound.play()
                    app.save_progress()
                self.dragging = None

    def draw_receipt(self, element, point, color):
        started, origin = self.receipts[element]
        age = self.elapsed - started
        app, ui = self.app, self.app.ui
        px, py = point
        cx, cy = self.mixing_center
        snap = smoothstep(age / .14)
        if snap < 1:
            ox, oy = origin
            orb_size = 51 - 13*snap
            app.source_images[element, 'orb'].draw(ox + (px-ox)*snap, oy + (py-oy)*snap, orb_size, orb_size)
        burst = (age-.11)/.35
        if 0 <= burst < 1:
            radius = 20 + 23*smoothstep(burst)
            for index in range(8):
                angle = math.tau*index/8 + burst*.32
                tx, ty = px + radius*math.cos(angle), py + radius*math.sin(angle)
                ui.diamond(tx, ty, 4*(1-burst), (*color, round(246*(1-burst))))
        flow = (age-.15)/.43
        if 0 <= flow < 1:
            step = 1 - (1-flow)**2
            strength = round(222*(1-flow*.65))
            app.p.draw_line(px, py, cx, cy, *color, strength)
            for trail in range(4):
                t = max(0, step - trail*.083)
                ui.diamond(px+(cx-px)*t, py+(cy-py)*t, 5-trail,
                           (*color, max(0, strength - trail*32)))

    def draw_activation(self, age):
        ui = self.app.ui
        cx, cy = self.mixing_center
        gather = smoothstep((age-.22)/.44)
        visibility = 1 - smoothstep((age-.63)/.23)
        for element, (px, py) in self.sockets.items():
            angle = math.atan2(py-cy, px-cx) + gather*1.1
            distance = 69*(1-gather)
            color = COLORS[element]
            for trail in range(5):
                radius = distance+4*trail
                theta = angle-trail*.14
                ui.diamond(cx+math.cos(theta)*radius, cy+math.sin(theta)*radius, 5-trail*.7,
                           (*color, round((245-trail*39)*visibility)))
        flash = max(0, 1 - abs(age-.68)/.24)
        if flash:
            radius = 16+46*smoothstep((age-.58)/.34)
            for i in range(12):
                angle = math.tau*i/12
                ui.diamond(cx+radius*math.cos(angle), cy+radius*math.sin(angle),
                           5*flash, (252, 211, 146, round(230*flash)))
            ui.diamond(cx, cy, 11*flash, (255, 244, 204, round(220*flash)))

    def draw(self):
        app, ui = self.app, self.app.ui
        x, y = self.center
        cx, cy = self.mixing_center
        guardian = app.room.guardian
        ui.begin()
        app.p.draw_rectangle(0, 0, app.width-1, app.height-1, 12, 9, 18, 185, filled=True)
        ui.panel(x-260, y-202, 520, 404, accent=True, radius=14)
        ui.text('오원 혼합기', x, y+166, 26)
        for element, (px, py) in self.sockets.items():
            filled = element in guardian.reward_orbs
            matching = element == self.dragging
            hovered = matching and math.dist(self.cursor, (px, py)) <= self.socket_radius
            color = COLORS[element]
            rim = (252, 228, 155) if hovered else color
            app.p.draw_line(cx, cy, px, py, *color, 156 if filled else 54)
            app.p.draw_circle(px, py, self.socket_radius, *rim, 255 if matching or filled else 152, filled=True)
            app.p.draw_circle(px, py, self.socket_radius-2, 32, 25, 43, filled=True)
            if not filled or element not in self.receipts or self.elapsed-self.receipts[element][0] >= .14:
                image = app.source_images[element, 'orb']
                image.opacify(1 if filled else .36)
                image.draw(px, py, 38, 38)
                image.opacify(1)
            ui.text(NAMES[element], px, py-37, 12, color)
        if self.ready:
            app.guardian_art.core(cx, cy, 19, self.elapsed)
        else:
            app.p.draw_circle(cx, cy, 32, 129, 106, 151, filled=True)
            app.p.draw_circle(cx, cy, 30, 27, 20, 37, filled=True)
            if self.activation_started is None:
                ui.text(f'{len(guardian.reward_orbs)} / {len(RITUAL)}', cx, cy, 18)
        for element in self.receipts:
            self.draw_receipt(element, self.sockets[element], COLORS[element])
        if self.activation_started is not None and not self.ready:
            self.draw_activation(self.elapsed-self.activation_started)
        for element, (px, py) in self.slots.items():
            ui.rounded(px-34, py-31, 68, 62, 8, (47, 58, 48, 255))
            if app.room.inventory[element] and element != self.dragging:
                app.source_images[element, 'orb'].draw(px, py, 48, 48)
            elif element in guardian.reward_orbs:
                ui.diamond(px, py, 7, COLORS[element])
            ui.text(NAMES[element], px, py-44, 12)
        if self.dragging:
            app.source_images[self.dragging, 'orb'].draw(*self.cursor, 56, 56)
        if self.ready:
            ui.key_label('F', '혼합 구슬 먹기', x, y-175, 23)
        elif self.activation_started is not None:
            ui.text('다섯 원소가 하나로 모이는 중', x, y-176, 14, ui.gold)
        else:
            ui.text('구슬을 같은 원소 자리에 끌어 놓기   ·   Esc 닫기', x, y-176, 14, ui.muted)
