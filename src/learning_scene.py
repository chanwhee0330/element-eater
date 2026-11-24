"""구슬 섭취부터 원소 모습 공개까지 재생하는 컷씬."""
import json
import math

from .elements import NAMES
from .boss import MIXED_INGEST_BITE, MIXED_INGEST_SECONDS, RITUAL
from .element_master_aura import draw_master_aura

# 효과별 첫 충격 프레임을 변신 시점에 맞춘다.
EFFECTS = {
    'water': ('splash', .16, 1.75, 1.8, (127, 215, 255)),
    'fire': ('fire-ring', .32, 2.6, 1.6, (255, 150, 70)),
    'wind': ('leaf-storm', .0, 1.25, 2.0, (183, 239, 139)),
    'earth': ('heavy-landing', .0, 1.5, 1.8, (231, 174, 105)),
    'lightning': ('thunderclap', .12, 1.6, 1.45, (217, 165, 255)),
}


def smoothstep(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


class TransformationEffects:
    def __init__(self, p, folder):
        self.sheets = {}
        for element, (name, *_) in EFFECTS.items():
            atlas = json.loads((folder / f'{name}.json').read_text(encoding='utf-8'))
            texture = p.load_image(str(folder / atlas['meta']['image']))
            self.sheets[element] = texture, atlas

    def draw_switch(self, element, x, foot, elapsed, scale):
        duration = .5
        if element not in self.sheets or elapsed >= duration:
            return
        opacity = 1 - smoothstep((elapsed - .14) / (duration - .14))
        self.draw(element, x, foot, elapsed, opacity, .48 * scale)

    def draw(self, element, x, foot, elapsed, opacity, zoom):
        _, start, speed, scale, _ = EFFECTS[element]
        image, atlas = self.sheets[element]
        spec = atlas['meta']['pixelfx']
        index = int((start + elapsed * speed) * spec['fps'])
        frames = atlas['frames']
        if index >= len(frames) or opacity <= 0:
            return
        frame = frames[index]['frame']
        width, height = frame['w'], frame['h']
        pivot_x, pivot_y = spec['pivot']
        scale *= zoom
        image.opacify(opacity)
        image.clip_draw(frame['x'], image.h - frame['y'] - height, width, height,
                        x + (width / 2 - pivot_x) * scale,
                        foot + (pivot_y - height / 2) * scale,
                        width * scale, height * scale)
        image.opacify(1)


class ElementCutscene:
    reveal_seconds = .93

    def __init__(self, room):
        self.source = next(source for source in room.sources if source.id == room.ingest_source)
        self.previous_form = room.ingest_form
        self.reveal_time = None

    @property
    def finished(self):
        return self.reveal_time is not None and self.reveal_time >= self.reveal_seconds

    def advance(self, room, dt):
        if self.reveal_time is not None:
            self.reveal_time += dt
            return False
        room.ingest_tick(dt)
        if room.ingest_elapsed >= 0:
            return False
        self.reveal_time = 0
        return True

    def draw(self, app):
        room, p, ui = app.room, app.p, app.ui
        player = room.player
        element = self.source.element
        *_, color = EFFECTS[element]
        reveal = self.reveal_time
        elapsed = room.ingest_elapsed if reveal is None else room.tuning.ingest_duration + reveal
        enter = smoothstep(elapsed / .23)
        leave = 1 if reveal is None else 1 - smoothstep((reveal - .56) / .37)
        framing = enter * leave
        focus = (player.x, player.y)
        normal_x, normal_y = app.point(*focus)
        x = round(normal_x + (app.width / 2 - normal_x) * framing)
        foot = round(normal_y + (app.height * .45 - normal_y) * framing)
        zoom = 1 + .33 * framing
        app.draw_cutscene_world(focus, (x, foot), zoom)

        ui.begin()
        shade = round(167 * framing)
        p.draw_rectangle(0, 0, app.width-1, app.height-1, 12, 11, 22, shade, filled=True)
        bars = round(62 * framing)
        if bars:
            p.draw_rectangle(0, 0, app.width-1, bars, 12, 10, 17, filled=True)
            p.draw_rectangle(0, app.height-bars, app.width-1, app.height-1, 12, 10, 17, filled=True)

        stage_scale = 1 + 1.65 * framing
        unit = app.unit * stage_scale
        scale = unit / room.data['heroReferenceHeight']
        ui.rounded(x-unit*.39, foot-6, unit*.78, 12, 6, (10, 8, 17, 180))
        if reveal is not None:
            app.transformation_effects.draw(element, x, foot, reveal, leave, .84 + .22 * framing)
        elif room.ingest_consumed:
            gather = (elapsed-room.tuning.ingest_event) / (room.tuning.ingest_duration-room.tuning.ingest_event)
            self.draw_gather(p, x, foot + unit*.54, gather, color)

        form = self.previous_form if reveal is None else element
        state = 'ingest' if reveal is None else 'idle'
        key = ('hero', state) if form == 'neutral' else ('hero', state, form)
        if reveal is None:
            index = min(7, int(elapsed * 12))
        else:
            index = int(reveal * 4)
        # 컷씬 안에서는 정면을 보여주고 복귀할 때 마지막 조준 방향을 다시 사용한다.
        facing = 'down' if framing > .2 else player.facing
        app.draw_actor_frame(key, facing, index, x, foot, scale)

        if not room.ingest_consumed and reveal is None:
            self.draw_orb(app, player, x, foot, unit, zoom)
        if reveal is not None:
            flash = 1 - smoothstep(reveal / .16)
            if flash > 0:
                ui.diamond(x, foot + unit*.56, 5 + 26*flash, (250, 243, 255, round(220*flash)))
            if .13 <= reveal < .84:
                opacity = smoothstep((reveal-.13)/.13) * (1 - smoothstep((reveal-.64)/.20))
                self.draw_caption(app, element, color, opacity)

    def draw_orb(self, app, player, x, foot, unit, zoom):
        source = self.source
        room = app.room
        progress = smoothstep(room.ingest_elapsed / room.tuning.ingest_event)
        dx, dy = app.view.project(source.x-player.x, source.y-player.y)
        lift = app.orb_lift(source)
        orb_x = x + dx * zoom * (1 - progress)
        orb_y = foot + (lift-dy) * zoom * (1 - progress) + unit*.43*progress
        orb_y += math.sin(math.pi*progress) * unit*.32
        size = (app.unit*zoom + unit*.4 * math.sin(math.pi*progress)) * (1 - .65*progress)
        app.source_images[source.element, 'orb'].draw(orb_x, orb_y, size, size)

    @staticmethod
    def draw_gather(p, x, y, progress, color):
        for index in range(14):
            angle = index * math.tau / 14 + progress*1.55
            orbit = (1 - progress) * (71 + (index % 3)*19) + 11
            px = round(x + math.cos(angle)*orbit)
            py = round(y + math.sin(angle)*orbit*.72)
            radius = 2 + index % 2
            alpha = round(235 * smoothstep(progress/.22))
            p.draw_rectangle(px-radius, py-radius, px+radius, py+radius, *color, alpha, filled=True)
            p.draw_rectangle(px, py, px+1, py+1, 249, 244, 255, alpha, filled=True)

    @staticmethod
    def draw_caption(app, element, color, opacity):
        ui = app.ui
        x, y = app.width / 2, app.height * .265
        text = f'{NAMES[element]} 원소 습득'
        width = ui.measure(text, 26) + 52
        ui.rounded(x-width/2, y-20, width, 42, 6, (20, 16, 28, round(220*opacity)))
        ui.p.draw_line(x-width/2+14, y-18, x+width/2-14, y-18, *color, round(190*opacity))
        text_color = tuple(round(24 + (channel-24)*opacity) for channel in color)
        ui.text(text, x, y+1, 26, text_color)


class MixedElementCutscene:
    """다섯 구슬이 합쳐지며 엘리먼트 마스터가 되는 연출."""
    source = None
    wave_times = (2.70, 2.89, 3.07, 3.24, 3.42)

    def __init__(self, room, sounds):
        self.elapsed = room.guardian.reward_scene_elapsed
        self.sounds = sounds

    @property
    def finished(self):
        return self.elapsed >= MIXED_INGEST_SECONDS

    def advance(self, room, dt):
        prior = self.elapsed
        self.elapsed += dt
        for index, element in enumerate(RITUAL):
            if prior < .82 + index*.23 <= self.elapsed:
                if sound := self.sounds.get(f'switch-{element}'):
                    sound.play()
        if prior < MIXED_INGEST_BITE <= self.elapsed:
            if sound := self.sounds.get('weakness'):
                sound.play()
        return room.guardian.advance_reward_scene(dt)

    def draw(self, app):
        room, p, ui = app.room, app.p, app.ui
        time = self.elapsed
        leave = 1 - smoothstep((time - 4.70)/.90)
        framing = smoothstep(time/.68) * leave
        focus = (room.player.x, room.player.y)
        normal_x, normal_y = app.point(*focus)
        x = round(normal_x + (app.width/2 - normal_x)*framing)
        foot = round(normal_y + (app.height*.43 - normal_y)*framing)
        zoom = 1 + .46*framing
        unit = app.unit * (1 + 1.82*framing)
        app.draw_cutscene_world(focus, (x, foot), zoom)

        ui.begin()
        p.draw_rectangle(0, 0, app.width-1, app.height-1, 10, 8, 22, round(183*framing), filled=True)
        bars = round(78*framing)
        if bars:
            p.draw_rectangle(0, 0, app.width-1, bars, 10, 8, 15, filled=True)
            p.draw_rectangle(0, app.height-bars, app.width-1, app.height-1, 10, 8, 15, filled=True)
        ui.rounded(x-unit*.36, foot-7, unit*.72, 14, 7, (9, 7, 14, round(177*framing)))
        self.draw_seal(app, x, foot, unit, framing)

        revealed = time >= MIXED_INGEST_BITE
        aura_time = room.elapsed + (time-MIXED_INGEST_SECONDS)*framing
        for element, start in zip(RITUAL, self.wave_times):
            age = time-start
            if 0 <= age < 1.2:
                opacity = (1-smoothstep((age-.43)/.77))*leave
                app.transformation_effects.draw(element, x, foot, age, opacity, 1.04)
        if revealed:
            draw_master_aura(app, x, foot, unit, aura_time, front=False)

        ingest_start = MIXED_INGEST_BITE-room.tuning.ingest_event
        ingest_end = ingest_start+room.tuning.ingest_duration
        ingesting = ingest_start <= time < ingest_end
        facing = 'down' if framing > .2 else room.player.facing
        index = min(7, int((time-ingest_start)*12)) if ingesting else int(time*4) % 8
        app.draw_actor_frame(('hero', 'ingest' if ingesting else 'idle'), facing, index, x, foot,
                             unit/room.data['heroReferenceHeight'])

        if revealed:
            draw_master_aura(app, x, foot, unit, aura_time, front=True)
            flash = 1-smoothstep((time-MIXED_INGEST_BITE)/.24)
            if flash > 0:
                ui.diamond(x, foot+unit*.53, 9+43*flash, (255, 247, 215, round(225*flash)))
            self.draw_title(app)
        else:
            self.draw_convergence(app, x, foot, unit, focus, zoom)

    def draw_seal(self, app, x, foot, unit, opacity):
        p, ui = app.p, app.ui
        reveal = smoothstep((self.elapsed-.46)/.66)
        wave = smoothstep((self.elapsed-MIXED_INGEST_BITE)/.92)
        if not reveal:
            return
        for ring, color in ((1.06, (222, 171, 111)), (1.47, (180, 123, 212)), (1.82, (116, 119, 211))):
            radius = unit * ring * (.68+.32*reveal+.32*wave)
            alpha = round((145-51*wave)*opacity*reveal)
            for index in range(44):
                a = math.tau*index/44
                b = math.tau*(index+.79)/44
                p.draw_line(x+radius*math.cos(a), foot+radius*.32*math.sin(a),
                            x+radius*math.cos(b), foot+radius*.32*math.sin(b), *color, alpha)
        for index, element in enumerate(RITUAL):
            *_, color = EFFECTS[element]
            angle = self.elapsed*.52 + index*math.tau/len(RITUAL)
            radius = unit*(1.33+.32*wave)
            ui.diamond(x+math.cos(angle)*radius, foot+math.sin(angle)*radius*.32,
                       6*reveal, (*color, round(210*opacity)))

    def draw_convergence(self, app, x, foot, unit, focus, zoom):
        time = self.elapsed
        mouth_y = foot+unit*.48
        boss = app.room.enemies[0]
        dx, dy = app.view.project(boss.x-focus[0], boss.y-focus[1])
        split = smoothstep((time-.56)/.56)
        gather = smoothstep((time-1.68)/(MIXED_INGEST_BITE-1.68))
        ring = (119 + unit*.41)*split*(1-gather)
        center_x = x+dx*zoom*(1-split)
        center_y = mouth_y + (unit*.52 + (1-split)*(-dy*zoom))*(1-gather)
        if split < 1:
            app.guardian_art.core(center_x, center_y, 17*(1-split), time)
        for index, element in enumerate(RITUAL):
            *_, color = EFFECTS[element]
            angle = time*(1.12+.78*gather)+math.tau*index/len(RITUAL)
            if split > 0:
                for trail in range(1, 8):
                    a = angle-trail*.10
                    app.ui.diamond(center_x+ring*math.cos(a), center_y+ring*.48*math.sin(a),
                                   (5-trail*.47)*split, (*color, round((196-17*trail)*split)))
                size = (15+33*split)*(1-.7*gather)
                app.source_images[element, 'orb'].draw(center_x+ring*math.cos(angle),
                                                        center_y+ring*.48*math.sin(angle), size, size)

    def draw_title(self, app):
        opacity = smoothstep((self.elapsed-3.22)/.42) * (1-smoothstep((self.elapsed-4.68)/.48))
        if opacity <= 0:
            return
        ui = app.ui
        x, y = app.width/2, app.height*.215
        if opacity > .98:
            ui.panel(x-190, y-27, 380, 62, accent=True)
        else:
            ui.rounded(x-190, y-27, 380, 62, 9, (20, 14, 31, round(235*opacity)))
        color = tuple(round(22+(value-22)*opacity) for value in (249, 228, 177))
        ui.text('엘리먼트 마스터', x, y+6, 26, color)
        for index, element in enumerate(RITUAL):
            *_, tint = EFFECTS[element]
            ui.diamond(x+(index-2)*21, y-14, 3, (*tint, round(221*opacity)))
