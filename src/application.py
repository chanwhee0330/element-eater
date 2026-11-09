"""pico2d 창·입력·고정 시간 갱신·아틀라스 렌더러."""
import importlib
import json
import sys
import time
import math

from .room import ROOT, Room
from .ui import GameUI
from .savegame import DEFAULT_SAVE, SaveStore, restore
from .title import draw_title, hit_test


class Application:
    width, height = 1000, 900
    unit, left, top = 36, 140, 64
    fixed_dt = 1 / 120
    menu = ('계속하기', '현재 방 재시작', '타이틀로 돌아가기', '게임 종료')

    def __init__(self, p, save_path=DEFAULT_SAVE):
        self.p = p
        self.room = Room()
        self.scene = 'title'
        self.save_store = SaveStore(save_path)
        self.continue_record = self.save_store.load()
        self.title_index = 1
        self.save_error = ''
        self.save_elapsed = 0
        self.finished_save = False
        self.keys = set()
        self.attack_queued = False
        self.actions = set()
        self.paused = False
        self.menu_index = 0
        self.running = True
        self.accumulator = 0
        self.images, self.metadata = {}, {}
        self.keymap = {p.SDLK_w:'w',p.SDLK_a:'a',p.SDLK_s:'s',p.SDLK_d:'d',p.SDLK_SPACE:'attack',
                       p.SDLK_f:'ingest',p.SDLK_r:'skill',p.SDLK_q:'previous',p.SDLK_e:'next'}
        self.load_room_images()
        self.title_image = p.load_image(str(ROOT / 'assets/ui/title/v1/title-screen-v1.png'))
        # 제자리 원거리형도 넉백 중에는 moving 상태가 되므로 walk 시트가 필요하다.
        for kind, states in [('hero', ('idle', 'walk', 'attack', 'ingest')), ('melee', ('idle', 'walk', 'attack')), ('ranged', ('idle', 'walk', 'attack'))]:
            for state in states:
                stem = (ROOT / f'assets/sprites/hero/neutral/hero-neutral-{state}' if kind == 'hero'
                        else ROOT / f'assets/sprites/enemies/elemental-v1/neutral/{kind}/enemy-neutral-{kind}-{state}')
                self.images[kind, state] = p.load_image(str(stem.with_suffix('.png')))
                self.metadata[kind, state] = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
                element = 'water' if kind == 'hero' else 'fire'
                stem = (ROOT / f'assets/sprites/hero/{element}/hero-{element}-{state}' if kind == 'hero'
                        else ROOT / f'assets/sprites/enemies/elemental-v1/{element}/{kind}/enemy-{element}-{kind}-{state}')
                self.images[kind, state, element] = p.load_image(str(stem.with_suffix('.png')))
                self.metadata[kind, state, element] = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
        self.shot_images, self.shot_metadata = {}, {}
        for element in ('neutral', 'water', 'fire'):
            shot_path = ROOT / f'assets/effects/basic-projectiles/v1/{element}-flight'
            self.shot_images[element] = p.load_image(str(shot_path.with_suffix('.png')))
            self.shot_metadata[element] = json.loads(shot_path.with_suffix('.json').read_text(encoding='utf-8'))
        self.source_images = {name: p.load_image(str(ROOT / f'assets/items/elements/break-release-v3/sprites/water-{name}.png'))
                              for name in ('idle','damaged1','damaged2','break','orb')}
        self.ui = GameUI(p, self.images['hero', 'idle'])
        self.font, self.small = self.ui.fonts[18], self.ui.fonts[14]

    def load_room_images(self):
        self.background = self.p.load_image(str(self.room.map_path.parent / self.room.data['image']))
        self.backdrop = self.p.load_image(str(self.room.map_path.parent / self.room.data['backdropImage']))

    def advance_stage(self):
        hp, inventory, selected = self.room.player.hp, dict(self.room.inventory), self.room.selected
        self.room = Room(stage=2)
        self.room.player.hp = hp
        self.room.inventory, self.room.selected = inventory, selected
        self.load_room_images()
        self.enter_play()
        self.save_progress()

    def pause(self, value):
        was_paused = self.paused
        if value and not self.paused:
            self.menu_index = 0
        self.paused = value
        self.keys.clear()
        self.attack_queued = False
        self.actions.clear()
        self.accumulator = 0
        if value and not was_paused and self.scene == 'play':
            self.save_progress()

    def save_progress(self):
        try:
            if self.room.outcome == 'clear':
                self.save_store.clear()
                self.continue_record = None
            elif not self.room.outcome:
                self.save_store.write(self.room)
            self.save_elapsed = 0
            self.save_error = ''
        except OSError as exc:
            self.save_error = '진행 상황을 저장하지 못했습니다.'
            print(f'{self.save_error} {exc}', file=sys.stderr)

    def enter_play(self):
        self.scene = 'play'
        self.finished_save = False
        self.pause(False)
        self.menu_index = 0
        self.save_elapsed = 0
        self.ui.last_time = self.room.elapsed
        self.ui.hp_trail = self.room.player.hp

    def new_game(self):
        self.room = Room()
        self.load_room_images()
        self.enter_play()
        self.save_progress()

    def continue_game(self):
        record = self.save_store.load()
        if record is None:
            self.continue_record = None
            self.title_index = 1
            return
        restore(record, self.room)
        self.load_room_images()
        self.continue_record = record
        self.enter_play()

    def return_to_title(self):
        self.save_progress()
        self.scene = 'title'
        self.pause(False)
        self.continue_record = self.save_store.load()
        self.title_index = 1

    def finish(self):
        if self.scene == 'play':
            self.save_progress()
        self.running = False

    def activate_title(self, index):
        if index == 0 and self.continue_record is not None:
            self.continue_game()
        elif index == 1:
            self.new_game()
        elif index == 2:
            self.finish()

    def handle_title(self, event):
        p = self.p
        if event.type in (p.SDL_MOUSEMOTION, p.SDL_MOUSEBUTTONDOWN):
            index = hit_test(event.x, self.height-event.y, self.width)
            if index is not None and (index != 0 or self.continue_record is not None):
                self.title_index = index
                if event.type == p.SDL_MOUSEBUTTONDOWN and event.button == p.SDL_BUTTON_LEFT:
                    self.activate_title(index)
        elif event.type == p.SDL_KEYDOWN:
            if event.key in (p.SDLK_LEFT, p.SDLK_a, p.SDLK_RIGHT, p.SDLK_d, p.SDLK_TAB):
                direction = -1 if event.key in (p.SDLK_LEFT, p.SDLK_a) else 1
                self.title_index = (self.title_index+direction) % 3
                if self.title_index == 0 and self.continue_record is None:
                    self.title_index = (self.title_index+direction) % 3
            elif event.key in (p.SDLK_RETURN, p.SDLK_SPACE):
                self.activate_title(self.title_index)

    def restart(self):
        self.room.reset()
        self.enter_play()
        self.save_progress()

    def activate_menu(self):
        if self.menu_index == 0:
            self.pause(False)
        elif self.menu_index == 1:
            self.restart()
        elif self.menu_index == 2:
            self.return_to_title()
        else:
            self.finish()

    def handle(self, events):
        p = self.p
        for event in events:
            if event.type == p.SDL_QUIT:
                self.finish()
            elif self.scene == 'title':
                self.handle_title(event)
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(self.keymap.get(event.key))
            elif event.type == p.SDL_KEYDOWN:
                if event.key == p.SDLK_ESCAPE:
                    self.pause(not self.paused)
                elif self.room.outcome and not self.paused:
                    if event.key == p.SDLK_RETURN:
                        self.restart()
                elif self.paused:
                    if event.key in (p.SDLK_UP, p.SDLK_w):
                        self.menu_index = (self.menu_index - 1) % len(self.menu)
                    elif event.key in (p.SDLK_DOWN, p.SDLK_s):
                        self.menu_index = (self.menu_index + 1) % len(self.menu)
                    elif event.key in (p.SDLK_RETURN, p.SDLK_SPACE):
                        self.activate_menu()
                elif event.key in self.keymap:
                    action = self.keymap[event.key]
                    if action in ('ingest','skill','previous','next'):
                        self.actions.add(action)
                    else:
                        self.keys.add(action)
                    if event.key == p.SDLK_SPACE:
                        self.attack_queued = True

    def step(self, dt, *, focused=None):
        if self.scene == 'title':
            return
        # 포커스 상실/최소화 시 정지한다. pico2d가 버리는 창 이벤트에 의존하지 않는다.
        if focused is None:
            focused = bool(self.p.SDL_GetWindowFlags(self.p.pico2d.window) & self.p.SDL_WINDOW_INPUT_FOCUS)
        if not focused:
            self.pause(True)
        if self.paused:
            return
        if not 0 < dt < float('inf'):
            return
        self.accumulator += min(dt, .25)
        while self.accumulator >= self.fixed_dt:
            self.room.update(self.keys | self.actions | ({'attack'} if self.attack_queued else set()), self.fixed_dt)
            self.attack_queued = False
            self.actions.clear()
            self.accumulator -= self.fixed_dt
            if self.room.outcome == 'clear' and self.room.stage == 1:
                self.advance_stage()
                return
        self.save_elapsed += min(dt, .25)
        if self.room.outcome and not self.finished_save:
            self.save_progress()
            self.finished_save = True
        elif not self.room.outcome and self.save_elapsed >= 2:
            self.save_progress()

    def point(self, x, y):
        return self.left + x * self.unit, self.height - self.top - y * self.unit

    def label(self, text, x, y, color=(222, 225, 205)):
        px, py = self.point(x, y)
        self.small.draw(px, py, text, color)

    def draw_actor(self, actor):
        attacking = actor.attack_elapsed >= 0
        ingesting = actor.kind == 'hero' and self.room.ingest_elapsed >= 0
        state = 'ingest' if ingesting else 'attack' if attacking else 'walk' if actor.moving else 'idle'
        element = (self.room.ingest_form if ingesting else self.room.selected) if actor.kind == 'hero' else actor.element
        key = (actor.kind,state) if element == 'neutral' else (actor.kind,state,element)
        meta, image = self.metadata[key], self.images[key]
        fps = meta.get('fps', 12 if attacking else 4 if state == 'idle' else 10)
        index = min(7,int(self.room.ingest_elapsed*12)) if ingesting else min(7, int(actor.attack_elapsed * 12)) if attacking else int(actor.animation_time * fps) % meta['layout']['columns']
        frame = meta['frames'][f'{actor.attack_facing if attacking else actor.facing}_{index}']
        clip, pivot = frame['pico2dClip'], frame['pivotPixelsTopLeft']
        width, height = meta['frameSize']['width'], meta['frameSize']['height']
        factor = 1
        if actor.falling > 0:
            factor = max(.08, actor.falling / self.room.data['preview']['fallSeconds'])
        scale = self.unit / self.room.data['heroReferenceHeight'] * factor
        root_x, root_y = self.point(actor.x, actor.y)
        # JSON은 왼쪽 위 원점, pico2d는 왼쪽 아래. 발밑 루트로부터 칸 중심 계산.
        center_x = root_x + (width / 2 - pivot['x']) * scale
        center_y = root_y + (pivot['y'] - height / 2) * scale
        alpha = factor
        if actor.kind == 'hero' and actor.invulnerable > 0 and int(self.room.elapsed * 18) % 2:
            alpha *= .4
        image.opacify(alpha)
        if actor.hit_flash > 0:
            self.p.SDL_SetTextureColorMod(image.texture, 255, 135, 135)
        image.clip_draw(clip['left'], clip['bottom'], clip['width'], clip['height'],
                        center_x, center_y, width * scale, height * scale)
        image.opacify(1)
        self.p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def draw_enemy_health(self, actor):
        x, y = self.point(actor.x, actor.y)
        self.ui.enemy_health(actor, x, y)

    def draw_shots(self):
        p = self.p
        for shot in self.room.projectiles:
            image, meta = self.shot_images[shot.element], self.shot_metadata[shot.element]
            frame = meta['frames'][f'right_{int(shot.age*12)%8}']['pico2dClip']
            x, y = self.point(shot.x, shot.y-.4)
            p.SDL_SetTextureColorMod(image.texture, *((255,255,255) if shot.element != 'neutral' else (195,235,188) if shot.owner == 'hero' else (255,125,80)))
            image.clip_composite_draw(frame['left'], frame['bottom'], frame['width'], frame['height'],
                math.atan2(-shot.dy, shot.dx), '', x, y, 42, 42)
            p.SDL_SetTextureColorMod(image.texture,255,255,255)

    def draw_source(self, source):
        if source.phase == 'consumed':
            return
        x, y = self.point(source.x, source.y)
        if source.phase == 'orb':
            x, y = self.point(source.x, source.y-.55-.04*math.sin(source.age*3))
            size = self.unit
            if self.room.ingest_source == source.id and not self.room.ingest_consumed:
                t = min(1,self.room.ingest_elapsed/self.room.tuning.ingest_event)
                tx,ty = self.point(self.room.player.x,self.room.player.y-.55)
                x,y,size = x+(tx-x)*t,y+(ty-y)*t,size*(1-.5*t)
            self.source_images['orb'].draw(x,y,size,size)
            return
        shake = math.sin(source.hit_time*80)*self.unit*.04*max(0,1-source.hit_time/.13)
        if source.phase == 'intact':
            image,frame,pivot,scale = self.source_images['idle'],128,(64,114),self.unit/self.room.data['heroReferenceHeight']
        else:
            image = self.source_images[source.phase if source.phase in ('damaged1','damaged2') else 'break']
            frame,pivot,scale = 256,(128,228),self.unit/self.room.data['heroReferenceHeight']/2
        image.clip_draw(source.frame()*frame,0,frame,frame,
                        x+shake+(frame/2-pivot[0])*scale,y+(pivot[1]-frame/2)*scale,frame*scale,frame*scale)
        if source.phase != 'breaking':
            self.ui.begin()
            for i in range(3):
                self.p.draw_circle(x+(i-1)*8,y+47,2,*((148,199,211) if i < source.hp else (75,80,72)),filled=True)

    def draw_hud(self):
        key = ('hero','idle') if self.room.selected == 'neutral' else ('hero','idle',self.room.selected)
        self.ui.portrait = self.images[key]
        self.ui.hud(self.room, self.width, self.height)
        if self.room.nearest_orb() is not None and self.room.ingest_elapsed < 0:
            self.ui.key_label('F','물 구슬 섭취',self.width/2,105,28,13)
        elif self.room.ingest_elapsed < 0 and any(s.phase in ('intact','damaged1','damaged2')
                and math.hypot(s.x-self.room.player.x,s.y-self.room.player.y)<2
                and self.room.line_clear(s.x,s.y,self.room.player.x,self.room.player.y) for s in self.room.sources):
            self.ui.key_label('SPACE','물 원천 파괴',self.width/2,105,52,13)

    def draw_exit(self):
        x, y = self.point(self.room.data['plannedExit']['x'], self.room.data['plannedExit']['y'])
        opened = self.room.exit_open
        color = (137, 211, 166) if opened else (111, 100, 76)
        self.p.draw_rectangle(x-17, y-5, x+17, y+36, 18, 27, 27, filled=True)
        self.p.draw_rectangle(x-17, y-5, x+17, y+36, *color)
        if opened:
            self.p.draw_rectangle(x-12, y, x+12, y+31, 63, 98, 77, filled=True)
            self.small.draw(x-30, y+52, '출구 개방', (168, 225, 178))
        else:
            for dx in (-9, 0, 9):
                self.p.draw_line(x+dx, y-2, x+dx, y+33, *color)

    def draw(self, present=True):
        p = self.p
        p.clear_canvas()
        if self.scene == 'title':
            draw_title(self)
            if present:
                p.update_canvas()
            return
        p.draw_rectangle(0, 0, self.width, self.height, 5, 12, 19, filled=True)
        self.backdrop.draw(self.width/2, self.height/2, self.width, self.height)
        w, h = self.room.data['columns'] * self.unit, self.room.data['rows'] * self.unit
        self.background.draw(self.left + w / 2, self.height - self.top - h / 2, w, h)
        self.draw_exit()
        actors = [a for a in [self.room.player, *self.room.enemies] if a.active]
        layers = [(a.y,False,a) for a in actors]+[(s.y,True,s) for s in self.room.sources if s.phase != 'consumed']
        for _,is_source,obj in sorted(layers,key=lambda item:item[0]):
            if is_source:
                self.draw_source(obj)
            else:
                self.draw_actor(obj)
                if obj.kind != 'hero' and not obj.falling:
                    self.draw_enemy_health(obj)
        self.draw_shots()
        for effect in self.room.feedback:
            age = effect.duration-effect.remaining
            x, y = self.point(effect.x, effect.y)
            if effect.text:
                color = (158,223,184) if effect.text.startswith('+') else (247,227,175) if effect.enemy_hit else (247,123,106)
                self.font.draw(x-7,y+age*30,effect.text,color)
            else:
                p.draw_circle(x, y, round(5+age*34), *( (227, 228, 171) if effect.enemy_hit else (233, 125, 83)))
        if self.room.spike_contact and int(self.room.elapsed * 8) % 2:
            x, y = self.point(self.room.player.x, self.room.player.y)
            p.draw_circle(x, y + 13, 18, 243, 102, 80)
        self.draw_hud()
        if self.room.outcome or self.paused:
            self.ui.modal(self.width,self.height,self.paused,self.menu,self.menu_index,self.room.outcome,self.room.stage)
        if present:
            p.update_canvas()

    def release(self):
        # SDL 종료 전에 텍스처를 해제한다.
        self.ui.release()
        self.images.clear()
        self.background = None
        self.backdrop = None
        self.shot_images.clear()
        self.source_images.clear()
        self.title_image = None


def run():
    try:
        p = importlib.import_module('pico2d')
    except ImportError:
        print('pico2d가 필요합니다. python -m pip install -r requirements.txt', file=sys.stderr)
        return 1
    app = None
    opened = False
    try:
        p.open_canvas(Application.width, Application.height, sync=True)
        opened = True
        p.hide_lattice()
        app = Application(p)
        previous = time.perf_counter()
        while app.running:
            begin = time.perf_counter()
            app.handle(p.get_events())
            if not app.running:
                break
            app.step(begin - previous)
            previous = begin
            app.draw()
            caption = '엘리먼트 이터' if app.scene == 'title' else f'엘리먼트 이터 · {app.room.stage}번 스테이지'
            p.SDL_SetWindowTitle(p.pico2d.window, caption.encode('utf-8'))
            time.sleep(max(0, 1 / 60 - (time.perf_counter() - begin)))
    except (OSError, RuntimeError) as exc:
        print(f'게임 실행 실패: {exc}', file=sys.stderr)
        return 1
    finally:
        if app:
            app.release()
        if opened:
            p.close_canvas()
    return 0
