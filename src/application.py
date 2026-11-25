"""pico2d 창·입력·고정 시간 갱신·아틀라스 렌더러."""
import ctypes
import importlib
import json
import sys
import time
import math

from .room import ROOT, Room, STAGES
from .boss import GUARDIAN_SHOT_LIFT, SUMMON_SHOCK_AT
from .elements import ELEMENTS, NAMES
from .element_master_aura import draw_master_aura
from .isometric import IsometricRoom, Mesh
from .ui import GameUI
from .savegame import DEFAULT_SAVE, SaveStore, restore
from .title import draw_title, hit_test
from .acquisition_art import AcquisitionArt, LIGHTNING_ORB_HEIGHT
from .garden_art import GardenArt
from .guardian_art import ENDING_RETURN_DELAY, PROLOGUE_SECONDS, GuardianArt
from .learning_scene import ElementCutscene, MixedElementCutscene, TransformationEffects, smoothstep
from .quarry_art import QuarryArt
from .orb_mixer import OrbMixer
from .animation_audio import CUES, animation_state, collect_animation_sounds, footsteps, mechanism_loops


class Application:
    width, height = 1000, 900
    unit = IsometricRoom.sprite_height
    fixed_dt = 1 / 120
    ambience_channel = 0
    mechanism_channels = (1, 2)
    stage_fade_out_seconds = .62
    stage_fade_in_seconds = 1.1
    menu = ('계속하기', '현재 방 재시작', '타이틀로 돌아가기', '게임 종료')
    stage_ambience = {
        0: 'sanctuary', 1: 'wind', 3: 'hearth', 4: 'wind',
        5: 'quarry', 6: 'power', 8: 'quarry', 10: 'sanctuary',
    }

    def __init__(self, p, save_path=DEFAULT_SAVE):
        self.p = p
        self.room = Room()
        self.scene = 'title'
        self.stage_fade_out = None
        self.stage_fade_in = None
        self.practice = False
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
                       p.SDLK_g:'connect',p.SDLK_f:'ingest',p.SDLK_r:'skill',p.SDLK_q:'previous',p.SDLK_e:'next',
                       p.SDLK_p:'debug-clear'}
        self.view = IsometricRoom(p, self.width, self.height)
        self.view.load(self.room)
        self.title_image = p.load_image(str(ROOT / 'assets/ui/title/v1/title-screen-v1.png'))
        # 제자리 원거리형도 넉백 중에는 moving 상태가 되므로 walk 시트가 필요하다.
        for kind, states in [('hero', ('idle', 'walk', 'attack', 'ingest')), ('melee', ('idle', 'walk', 'attack')), ('ranged', ('idle', 'walk', 'attack'))]:
            for state in states:
                elements = ('neutral', 'water', 'fire', 'wind', 'earth', 'lightning')
                for element in elements:
                    if kind == 'hero':
                        stem = ROOT / f'assets/sprites/hero/{element}/hero-{element}-{state}'
                    else:
                        stem = ROOT / f'assets/sprites/enemies/elemental-v1/{element}/{kind}/enemy-{element}-{kind}-{state}'
                    key = (kind, state) if element == 'neutral' else (kind, state, element)
                    self.images[key] = p.load_image(str(stem.with_suffix('.png')))
                    self.metadata[key] = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
        self.shot_images, self.shot_metadata = {}, {}
        for element in ('neutral', 'water', 'fire', 'wind', 'earth', 'lightning'):
            shot_path = ROOT / f'assets/effects/basic-projectiles/v1/{element}-flight'
            self.shot_images[element] = p.load_image(str(shot_path.with_suffix('.png')))
            self.shot_metadata[element] = json.loads(shot_path.with_suffix('.json').read_text(encoding='utf-8'))
        source_folder = ROOT / 'assets/items/elements/break-release-v3/sprites'
        self.source_images = {
            (element, name): p.load_image(str(source_folder / f'{element}-{name}.png'))
            for element in ('water', 'fire', 'wind', 'earth', 'lightning') for name in ('idle','damaged1','damaged2','break','orb')
        }
        vine_folder = STAGES[3].parent
        self.vine_image = p.load_image(str(vine_folder / 'vine-burn.png'))
        self.vine_frames = json.loads((vine_folder / 'vine-burn.json').read_text(encoding='utf-8'))['frames']
        puzzle_folder = STAGES[4].parent
        self.block_image = p.load_image(str(puzzle_folder / 'puzzle-block.png'))
        self.gate_image = p.load_image(str(puzzle_folder / 'stone-gate.png'))
        power_folder = STAGES[6].parent
        self.conductor_images = [p.load_image(str(power_folder / f'conductor-{level}.png')) for level in range(4)]
        self.connect_image = p.load_image(str(power_folder / 'connect-switch.png'))
        flame_path = ROOT / 'assets/effects/fire/campfire/campfire.json'
        flame_sheet = json.loads(flame_path.read_text(encoding='utf-8'))
        self.flame_image = p.load_image(str(flame_path.with_name(flame_sheet['meta']['image'])))
        self.flame_frames = [frame['frame'] for frame in flame_sheet['frames']]
        self.flame_spec = flame_sheet['meta']['pixelfx']
        self.stage_keys = {
            key: stage for stage in STAGES if stage < 10
            for key in (getattr(p, f'SDLK_{stage}'), getattr(p, f'SDLK_KP_{stage}'))
        }
        self.stage_keys.update({p.SDLK_BACKQUOTE: 0, p.SDLK_0: 10, p.SDLK_KP_0: 10})
        orb_icons = {element: self.source_images[element, 'orb'] for element in ELEMENTS}
        self.ui = GameUI(p, self.images['hero', 'idle'], orb_icons)
        self.font = self.ui.fonts[18]
        self.acquisition_art = AcquisitionArt(self)
        self.transformation_effects = TransformationEffects(p, ROOT / 'assets/effects/acquisition')
        self.cutscene_background = p.SDL_CreateTexture(p.pico2d.renderer, p.SDL_PIXELFORMAT_RGBA8888,
                                                        p.SDL_TEXTUREACCESS_TARGET, self.width, self.height)
        if not self.cutscene_background:
            raise RuntimeError('원소 습득 컷씬 화면을 만들 수 없습니다.')
        self.ingest_cutscene = None
        self.ending_elapsed = 0
        self.orb_mixer = None
        self.prologue_read_elapsed = None
        self.garden_art = None
        self.guardian_art = None
        self.quarry_art = None
        self.trial_waterwheel = None
        self.trial_conductor_sheet = None
        self.trial_cutscene = None
        self.sounds = {}
        self.background_music = None
        self.background_music_request = None
        self.ambience = None
        self.ambience_request = None
        self.mechanism_sounds = [None] * len(self.mechanism_channels)
        if p.pico2d.audio_on:
            p.Mix_ReserveChannels(self.mechanism_channels[-1] + 1)
            sound_folder = ROOT / 'assets/audio/gameplay'
            for cue in (*(f'switch-{element}' for element in ELEMENTS), 'weakness', 'blocked',
                        'player-hit', 'player-attack', 'enemy-hit', *CUES):
                try:
                    self.sounds[cue] = p.load_wav(str(sound_folder / f'{cue}.wav'))
                except OSError:
                    continue
                if cue.startswith('loop-'):
                    self.sounds[cue].set_volume(9)
                elif cue in ('footstep', 'prologue-smoke'):
                    self.sounds[cue].set_volume(64)
            if 'weakness' in self.sounds:
                self.sounds['boss-shatter'] = self.sounds['weakness']
            water_footstep = sound_folder / 'footstep-water.wav'
            if water_footstep.is_file():
                try:
                    self.sounds['footstep-water'] = p.load_wav(str(water_footstep))
                    self.sounds['footstep-water'].set_volume(64)
                except OSError:
                    pass

    def set_ambience(self, name):
        if name == self.ambience_request or not self.p.pico2d.audio_on:
            return
        self.ambience_request = name
        if self.ambience is not None:
            self.p.Mix_HaltChannel(self.ambience_channel)
            self.ambience = None
        if name is None:
            return
        try:
            track = self.p.load_wav(str(ROOT / 'assets/audio/ambience' / f'{name}.wav'))
        except OSError:
            return
        track.set_volume(8)
        self.p.Mix_PlayChannel(self.ambience_channel, track.wav, -1)
        self.ambience = track

    def set_background_music(self, name):
        if name == self.background_music_request or not self.p.pico2d.audio_on:
            return
        self.background_music_request = name
        if self.background_music is not None:
            self.background_music.stop()
            self.background_music = None
        if name is None:
            return
        try:
            track = self.p.load_music(str(ROOT / 'assets/audio/music' / f'{name}.wav'))
        except OSError:
            return
        track.set_volume(12)
        track.repeat_play()
        self.background_music = track

    def refresh_background_music(self):
        guardian = self.room.guardian
        appeared = guardian is not None and guardian.summon >= SUMMON_SHOCK_AT
        self.set_background_music('boss' if appeared else 'dungeon')

    def refresh_ambience(self):
        room = self.room
        if room.reservoir:
            water = room.reservoir_opening > .18
        elif room.garden:
            water = room.sluice_wheel and room.sluice_pump
        elif room.trial:
            water = 0 < room.gate_time < room.gate_open_seconds or room.trial_flow(0) > 0
        else:
            self.set_ambience(self.stage_ambience.get(room.stage))
            return
        fire = len(room.extinguished) < len(room.fire_barriers)
        if water:
            self.set_ambience('water-and-fire' if fire else 'water')
        else:
            self.set_ambience('hearth' if fire else None)

    def advance_stage(self):
        previous = self.room
        if previous.lightning_attack:
            previous.lightning_charged = not previous.player.attack_emitted
            previous.finish_lightning_attack()
        self.room = Room(stage=previous.stage + 1)
        self.room.player.hp = previous.player.hp
        self.room.inventory = dict(previous.inventory)
        self.room.selected = previous.selected
        self.room.lightning_charged = previous.lightning_charged and self.room.selected == 'lightning'
        self.enter_play()
        self.stage_fade_in = 0.0
        self.save_progress()

    @property
    def fading_stage(self):
        return self.stage_fade_out is not None or self.stage_fade_in is not None

    def step_stage_fade(self, dt):
        if self.stage_fade_out is not None:
            self.stage_fade_out += dt
            if self.stage_fade_out >= self.stage_fade_out_seconds:
                self.advance_stage()
        else:
            self.stage_fade_in += dt
            if self.stage_fade_in >= self.stage_fade_in_seconds:
                self.stage_fade_in = None

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
        if self.practice or self.room.stage == 0:
            self.save_elapsed = 0
            return
        try:
            if self.room.outcome == 'clear' and self.room.stage + 1 not in STAGES:
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
        if self.room.garden or self.room.quarry or self.room.trial:
            self.room.preload_reference_paths()
        self.view.load(self.room)
        if self.room.guardian:
            if self.guardian_art is None:
                self.guardian_art = GuardianArt(self)
        else:
            self.guardian_art = None
        self.unit = self.view.sprite_height * (1 if self.room.data.get('layoutRevision') else self.view.reference_scale)
        self.scene = 'play'
        self.set_prologue_effect_volume(self.room.stage == 0)
        self.refresh_background_music()
        self.refresh_ambience()
        self.set_mechanism_sounds(mechanism_loops(self.room))
        self.stage_fade_out = None
        self.stage_fade_in = 0.0 if self.room.stage == 1 and self.room.elapsed == 0 else None
        self.ending_elapsed = 0
        self.orb_mixer = None
        self.prologue_read_elapsed = None
        self.finished_save = False
        self.pause(False)
        self.menu_index = 0
        self.save_elapsed = 0
        self.ui.last_time = self.room.elapsed
        self.ui.hp_trail = self.room.player.hp
        self.trial_cutscene = None
        if self.room.guardian and self.room.guardian.reward_scene_elapsed is not None:
            self.ingest_cutscene = MixedElementCutscene(self.room, self.sounds)
        else:
            self.ingest_cutscene = ElementCutscene(self.room) if self.room.ingest_elapsed >= 0 else None
        if self.room.trial:
            if self.room.plate_pressed and not self.room.stone_gate_open:
                self.start_trial_drain_cutscene()
            elif 0 in self.room.trial_returns and not self.room.trial_wheel_open:
                remaining = self.room.trial_wheel_reveal_seconds - self.room.trial_wheel_time
                self.trial_cutscene = ('wheel', self.room.elapsed + remaining + .75)

    def new_game(self, stage=1, *, practice=False):
        self.practice = practice
        self.room = Room(stage=stage)
        self.enter_play()
        if stage == 0 and not practice:
            try:
                self.save_store.clear()
                self.continue_record = None
                self.save_error = ''
            except OSError as exc:
                self.save_error = '이전 진행 상황을 초기화하지 못했습니다.'
                print(f'{self.save_error} {exc}', file=sys.stderr)
        self.save_progress()

    def continue_game(self):
        record = self.save_store.load()
        if record is None:
            self.continue_record = None
            self.title_index = 1
            return
        restore(record, self.room)
        self.practice = False
        self.continue_record = record
        self.enter_play()

    def return_to_title(self):
        self.save_progress()
        self.scene = 'title'
        self.set_prologue_effect_volume(False)
        self.set_background_music(None)
        self.set_ambience(None)
        self.set_mechanism_sounds((None, None))
        self.pause(False)
        self.continue_record = self.save_store.load()
        self.title_index = 1

    def finish(self):
        if self.scene == 'play' and self.stage_fade_out is not None:
            self.advance_stage()
        elif self.scene == 'play':
            self.save_progress()
        self.running = False

    def activate_title(self, index):
        if index == 0 and self.continue_record is not None:
            self.continue_game()
        elif index == 1:
            self.new_game(0)
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

    @property
    def ending(self):
        return self.room.guardian is not None and self.room.outcome == 'clear'

    def handle(self, events):
        p = self.p
        for event in events:
            if event.type == p.SDL_QUIT:
                self.finish()
            elif event.type == p.SDL_KEYDOWN and event.key in self.stage_keys:
                if not getattr(event, 'repeat', False):
                    self.new_game(self.stage_keys[event.key], practice=True)
            elif self.scene == 'title':
                self.handle_title(event)
            elif self.fading_stage:
                continue
            elif self.orb_mixer:
                self.orb_mixer.handle(event)
            elif event.type == p.SDL_KEYUP:
                self.keys.discard(self.keymap.get(event.key))
            elif event.type == p.SDL_KEYDOWN:
                if self.ending:
                    if (self.ending_elapsed >= ENDING_RETURN_DELAY
                            and event.key in (p.SDLK_RETURN, p.SDLK_ESCAPE)):
                        self.return_to_title()
                elif event.key == p.SDLK_ESCAPE:
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
                    if action in ('connect','ingest','skill','previous','next','debug-clear'):
                        if not self.ingest_cutscene and not getattr(event, 'repeat', False):
                            self.actions.add(action)
                    else:
                        self.keys.add(action)
                    if event.key == p.SDLK_SPACE and not self.ingest_cutscene:
                        self.attack_queued = True

    def step_ingest_cutscene(self):
        room = self.room
        if self.ingest_cutscene is None and not room.outcome:
            if room.guardian and room.guardian.reward_scene_elapsed is not None:
                self.ingest_cutscene = MixedElementCutscene(room, self.sounds)
                self.keys.clear()
                self.save_progress()
            elif room.ingest_elapsed >= 0 or ('ingest' in self.actions and room.start_ingest()):
                self.ingest_cutscene = ElementCutscene(room)
        cutscene = self.ingest_cutscene
        if cutscene is None:
            return False
        if cutscene.advance(room, self.fixed_dt):
            self.save_progress()
        if cutscene.finished:
            self.ingest_cutscene = None
        return True

    @property
    def near_prologue_tablet(self):
        player = self.room.player
        return math.dist((player.x, player.y), self.room.guardian.spec['center']) <= 1.35

    def step_prologue(self, dt):
        room, player = self.room, self.room.player
        room.elapsed += dt
        was_moving = player.moving
        previous_time = player.animation_time
        if self.prologue_read_elapsed is None:
            dx = int('d' in self.keys) - int('a' in self.keys)
            dy = int('s' in self.keys) - int('w' in self.keys)
            step = room.data['preview']['playerSpeed'] * dt / (math.hypot(dx, dy) or 1)
            room.move(player, dx * step, dy * step, safe=True)
            self.view.follow(player.x, player.y)
            if 'ingest' in self.actions and self.near_prologue_tablet:
                player.moving = False
                self.prologue_read_elapsed = 0
                self.play_sound('lever')
        else:
            previous = self.prologue_read_elapsed
            self.prologue_read_elapsed += dt
            if previous < 4.25 <= self.prologue_read_elapsed:
                self.play_sound('prologue-smoke')
            if self.prologue_read_elapsed >= PROLOGUE_SECONDS:
                self.advance_stage()
                return
        player.animate(dt, was_moving)
        if cue := footsteps(player, previous_time, player=True):
            self.play_sound(cue)
        self.actions.clear()
        self.attack_queued = False

    def set_prologue_effect_volume(self, in_prologue):
        for cue, sound in self.sounds.items():
            if cue not in ('footstep', 'footstep-water', 'prologue-smoke') and not cue.startswith('loop-'):
                sound.set_volume(64 if in_prologue else 128)

    def play_sound(self, cue):
        sound = self.sounds.get(cue)
        if sound is None and cue == 'footstep-water':
            sound = self.sounds.get('footstep')
        if sound is not None:
            sound.play()

    def set_mechanism_sounds(self, cues):
        for index, (channel, cue) in enumerate(zip(self.mechanism_channels, cues)):
            sound = self.sounds.get(cue)
            if sound is self.mechanism_sounds[index]:
                continue
            if self.mechanism_sounds[index] is not None:
                self.p.Mix_HaltChannel(channel)
            if sound is not None:
                self.p.Mix_PlayChannel(channel, sound.wav, -1)
            self.mechanism_sounds[index] = sound

    def step(self, dt, *, focused=None):
        if self.scene == 'title' or not 0 < dt < float('inf'):
            return
        if self.ending:
            self.ending_elapsed += min(dt, .05)
            return
        # 포커스 상실/최소화 시 정지한다. pico2d가 버리는 창 이벤트에 의존하지 않는다.
        if focused is None:
            focused = bool(self.p.SDL_GetWindowFlags(self.p.pico2d.window) & self.p.SDL_WINDOW_INPUT_FOCUS)
        if self.fading_stage:
            if focused:
                self.step_stage_fade(min(dt, .05))
            return
        if not focused:
            self.orb_mixer = None
            self.pause(True)
        if self.paused:
            return
        if self.orb_mixer:
            self.orb_mixer.elapsed += min(dt, .05)
            return
        if self.room.stage == 0:
            self.step_prologue(min(dt, .05))
            return
        if ('connect' in self.actions and self.room.can_claim_final_reward
                and not self.room.guardian.reward_loaded):
            self.pause(False)
            self.orb_mixer = OrbMixer(self)
            return
        plate_was_pressed = self.room.plate_pressed
        was_water_running = self.room.trial_flow(0) >= .8 if self.room.trial else False
        self.accumulator += min(dt, .25)
        while self.accumulator >= self.fixed_dt:
            if not self.step_ingest_cutscene():
                previous = animation_state(self.room)
                self.room.update(self.keys | self.actions | ({'attack'} if self.attack_queued else set()),
                                 self.fixed_dt)
                collect_animation_sounds(self.room, previous)
                self.refresh_background_music()
                self.refresh_ambience()
                self.set_mechanism_sounds(mechanism_loops(self.room))
            for cue in dict.fromkeys(self.room.sound_events):
                self.play_sound(cue)
            self.room.sound_events.clear()
            self.attack_queued = False
            self.actions.clear()
            self.accumulator -= self.fixed_dt
            if self.room.outcome == 'clear' and self.room.stage + 1 in STAGES:
                self.pause(False)
                self.stage_fade_out = 0.0
                return
        if self.room.trial and not self.room.debug_cleared:
            if self.room.plate_pressed and not plate_was_pressed:
                self.start_trial_drain_cutscene()
            elif not was_water_running and self.room.trial_flow(0) >= .8:
                self.trial_cutscene = ('wheel', self.room.elapsed + 1.65)
        player = self.room.player
        self.view.follow(*(self.room.safe[:2] if player.falling else (player.x, player.y)))
        self.save_elapsed += min(dt, .25)
        if self.room.outcome and not self.finished_save:
            self.save_progress()
            self.finished_save = True
        elif not self.room.outcome and self.save_elapsed >= 2:
            self.save_progress()

    def point(self, x, y, z=0):
        return self.view.point(x, y, z)

    def draw_actor_frame(self, key, facing, index, x, foot, scale, alpha=1, tint=None, *, angle=0):
        frame = self.metadata[key]['frames'][f'{facing}_{index}']
        clip, pivot = frame['pico2dClip'], frame['pivotPixelsTopLeft']
        width, height = clip['width'], clip['height']
        image = self.images[key]
        image.opacify(alpha)
        if tint:
            self.p.SDL_SetTextureColorMod(image.texture, *tint)
        dx, dy = (width / 2 - pivot['x']) * scale, (pivot['y'] - height / 2) * scale
        if angle:
            image.clip_composite_draw(clip['left'], clip['bottom'], width, height, angle, '',
                                      x + math.cos(angle)*dx - math.sin(angle)*dy,
                                      foot + math.sin(angle)*dx + math.cos(angle)*dy,
                                      width * scale, height * scale)
        else:
            image.clip_draw(clip['left'], clip['bottom'], width, height, x + dx, foot + dy,
                            width * scale, height * scale)
        image.opacify(1)
        if tint:
            self.p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def draw_actor(self, actor):
        if self.room.garden or self.room.quarry:
            x, y = self.point(actor.x, actor.y)
            if not (-65 <= x <= self.width + 65 and -120 <= y <= self.height + 60):
                return
        attacking = actor.attack_elapsed >= 0
        ingesting = actor.kind == 'hero' and self.room.ingest_elapsed >= 0
        state = 'ingest' if ingesting else 'attack' if attacking else 'walk' if actor.moving else 'idle'
        element = actor.element
        if actor.kind == 'hero':
            element = self.room.ingest_form if ingesting else self.room.selected
            if attacking and self.room.lightning_attack:
                element = actor.attack_element
        key = (actor.kind,state) if element == 'neutral' else (actor.kind,state,element)
        meta = self.metadata[key]
        fps = meta.get('fps', 12 if attacking else 4 if state == 'idle' else 10)
        index = min(7,int(self.room.ingest_elapsed*12)) if ingesting else min(7, int(actor.attack_elapsed * 12)) if attacking else int(actor.animation_time * fps) % meta['layout']['columns']
        factor = 1
        if actor.falling > 0:
            factor = max(.08, actor.falling / self.room.data['preview']['fallSeconds'])
        scale = self.unit / self.room.data['heroReferenceHeight'] * factor
        root_x, root_y = self.point(actor.x, actor.y, -38 * (1 - factor))
        if not actor.falling:
            self.view.draw_shadow(actor.x, actor.y)
        switch_started = self.room.element_switch_started
        if actor.kind == 'hero' and switch_started is not None and not (ingesting or actor.falling):
            self.transformation_effects.draw_switch(element, root_x, root_y,
                                                    self.room.elapsed - switch_started,
                                                    self.unit / self.view.sprite_height)
        alpha = factor
        if actor.kind == 'hero' and actor.invulnerable > 0 and int(self.room.elapsed * 18) % 2:
            alpha *= .4
        tint = (255, 135, 135) if actor.hit_flash > 0 else None
        collapse = min(1, max(0, ((self.prologue_read_elapsed or 0) - 5.26) / .5))
        mastered = actor.kind == 'hero' and self.room.guardian and self.room.guardian.reward_tasted
        if mastered:
            draw_master_aura(self, root_x, root_y, self.unit, self.room.elapsed, front=False)
        self.draw_actor_frame(key, actor.attack_facing if attacking else actor.facing, index,
                              root_x, root_y, scale, alpha, tint, angle=-1.43 * collapse**2)
        if mastered:
            draw_master_aura(self, root_x, root_y, self.unit, self.room.elapsed, front=True)

        if actor.kind == 'hero':
            self.draw_lightning_charge(actor, root_x, root_y)
        elif not actor.falling and not self.ingest_cutscene:
            self.ui.enemy_health(actor, root_x, root_y, offset=62 * self.view.reference_scale)

    def draw_shot(self, shot):
        p = self.p
        if shot.element == 'mixed':
            self.guardian_art.mixed_projectile(shot)
            return
        image, meta = self.shot_images[shot.element], self.shot_metadata[shot.element]
        frame = meta['frames'][f'right_{int(shot.age * 12) % 8}']['pico2dClip']
        lift = self.view.tile_height*GUARDIAN_SHOT_LIFT if self.room.guardian else 21
        x,y = self.point(shot.x,shot.y,lift)
        dx, dy = self.view.project(shot.dx, shot.dy)
        if shot.element == 'neutral':
            tint = (195, 235, 188) if shot.owner == 'hero' else (255, 125, 80)
            p.SDL_SetTextureColorMod(image.texture, *tint)
        image.clip_composite_draw(frame['left'], frame['bottom'], frame['width'], frame['height'],
                                  math.atan2(-dy, dx), '', x, y, 46, 46)
        p.SDL_SetTextureColorMod(image.texture, 255, 255, 255)

    def orb_lift(self, source):
        height = LIGHTNING_ORB_HEIGHT if self.room.capacitor and source.id == 'first-orb' else self.unit * .55
        lift = height + self.unit * .04 * math.sin(source.age * 3)
        if source.id == 'first-orb' and not (self.room.reservoir or self.room.forge or self.room.windmill or self.room.capacitor):
            lift += self.unit * .92 * (1 - min(1, source.age / .48)) ** 2
        return lift

    def draw_source(self, source):
        if source.phase in ('sealed', 'consumed'):
            return
        if source.phase == 'gathering':
            self.acquisition_art.draw_wind_orb(source)
            return
        if source.phase == 'charging':
            self.acquisition_art.draw_lightning_orb(source)
            return
        if source.phase == 'descending':
            if source.age < .13:
                return
            x, y = self.acquisition_art.reservoir_orb_position(source)
            size = self.unit * (.72 + .28 * min(1, (source.age-.13)/.27))
            self.source_images[source.element, 'orb'].draw(x, y, size, size)
            return
        if source.phase == 'igniting':
            progress = source.age / self.room.forge['releaseSeconds']
            if progress >= .48:
                rise = min(1, (progress - .48) / .52)
                x, y = self.point(source.x, source.y, 7 + (self.unit*.55-7)*rise)
                size = self.unit * (.55 + .45*rise)
                self.source_images[source.element, 'orb'].draw(x, y, size, size)
            return
        x, y = self.point(source.x, source.y)
        self.view.draw_shadow(source.x, source.y)
        if source.phase == 'orb':
            y += self.orb_lift(source)
            size = self.unit
            if self.room.ingest_source == source.id and not self.room.ingest_consumed:
                t = min(1,self.room.ingest_elapsed/self.room.tuning.ingest_event)
                tx,ty = self.point(self.room.player.x, self.room.player.y, self.unit * .55)
                x,y,size = x+(tx-x)*t,y+(ty-y)*t,size*(1-.5*t)
            self.source_images[source.element, 'orb'].draw(x,y,size,size)
            return
        shake = math.sin(source.hit_time*80)*self.unit*.04*max(0,1-source.hit_time/.13)
        if source.phase == 'intact':
            image,frame,pivot,scale = self.source_images[source.element, 'idle'],128,(64,114),self.unit/self.room.data['heroReferenceHeight']
        else:
            image = self.source_images[source.element, source.phase if source.phase in ('damaged1','damaged2') else 'break']
            frame,pivot,scale = 256,(128,228),self.unit/self.room.data['heroReferenceHeight']/2
        image.clip_draw(source.frame()*frame,0,frame,frame,
                        x+shake+(frame/2-pivot[0])*scale,y+(pivot[1]-frame/2)*scale,frame*scale,frame*scale)
        if source.phase != 'breaking':
            self.ui.begin()
            for i in range(3):
                self.p.draw_circle(x+(i-1)*8,y+64 * self.view.reference_scale,2,*((148,199,211) if i < source.hp else (75,80,72)),filled=True)

    def draw_hud(self):
        key = ('hero','idle') if self.room.selected == 'neutral' else ('hero','idle',self.room.selected)
        self.ui.portrait = self.images[key]
        if self.room.ingest_elapsed < 0:
            orb = self.room.nearest_orb()
            if orb is not None:
                self.draw_prompt(orb, 'F', f'{NAMES[orb.element]} 구슬 섭취', 28)
            else:
                player = self.room.player
                nearby = [s for s in self.room.sources if s.phase in ('intact', 'damaged1', 'damaged2')
                          and math.hypot(s.x - player.x, s.y - player.y) < 2
                          and self.room.line_clear(s.x, s.y, player.x, player.y)]
                if nearby:
                    source = min(nearby, key=lambda s: math.hypot(s.x - player.x, s.y - player.y))
                    self.draw_prompt(source, 'SPACE', f'{NAMES[source.element]} 원천 파괴', 50)
        self.ui.hud(self.room, self.width, self.height)

    def draw_prompt(self, source, key, label, key_width):
        height = 91
        if source.id == 'first-orb':
            if self.room.forge:
                height = 165
            elif self.room.capacitor:
                height = 116
        x, y = self.point(source.x, source.y, height)
        x = max(100, min(self.width - 100, x))
        self.ui.begin()
        self.ui.panel(x - 88, y - 17, 176, 34, accent=True)
        self.ui.key_label(key, label, x, y, key_width, 13)

    def draw_vine(self, gate, burn_time):
        frame = self.vine_frames[0]
        if burn_time >= 0:
            remaining = burn_time * 1000
            for frame in self.vine_frames[1:]:
                remaining -= frame['durationMs']
                if remaining < 0:
                    break
        x, y = self.point(gate['x'] + gate['width'] / 2, gate['y'] + gate['height'])
        clip, pivot = frame['pico2dClip'], frame['pivotPixelsTopLeft']
        width, height = clip['width'], clip['height']
        unit = self.view.tile_width
        pieces = math.ceil(gate['width'] / 2.65) if self.room.stage in (7, 8, 9) else 1
        span = gate['width'] * unit / pieces
        scale = span / (width * .82)
        left, top = gate['x'], gate['y']
        lift = self.view.foliage_lift((left, top, left + gate['width'], top + gate['height']))
        for index in range(pieces):
            center = x + (index + .5 - pieces / 2) * span
            self.vine_image.clip_draw(clip['left'], clip['bottom'], width, height,
                                      center, y + lift + (pivot['y'] - height / 2) * scale,
                                      width * scale, height * scale)
        player = self.room.player
        can_burn = not self.room.forge or self.room.inventory['fire']
        if self.room.fire_barriers and can_burn and burn_time < 0 and math.hypot(
                player.x - gate['x'] - gate['width'] / 2, player.y - gate['y'] - gate['height']) < 3:
            self.ui.key_label('SPACE', '불로 덩굴 태우기', x, y - 15, 45, 12)

    def draw_fire_barrier(self, index):
        left, top, right, bottom = self.room.fire_barriers[index]
        vertical = bottom - top > right - left
        count = max(1, round(max(right - left, bottom - top) * 1.6))
        y = (top + bottom) / 2
        scale = self.view.reference_scale
        if index not in self.room.extinguished:
            pivot_y = self.flame_spec['pivot'][1]
            frame_time = int(self.room.elapsed * self.flame_spec['fps'])
            for column in range(count):
                frame = self.flame_frames[(frame_time + 7 * column + index * 5) % len(self.flame_frames)]
                fraction = (column + .5) / count
                x = (left + right) / 2 if vertical else left + fraction * (right - left)
                px, py = self.point(x, top + fraction * (bottom - top) if vertical else y)
                width, height = frame['w'], frame['h']
                flame_scale = .82 * scale
                self.flame_image.clip_draw(frame['x'], self.flame_image.h - frame['y'] - height,
                                           width, height, px, py + (pivot_y - height / 2) * flame_scale,
                                           width * flame_scale, height * flame_scale)
            player = self.room.player
            x = (left + right) / 2
            if math.hypot(player.x - x, player.y - y) < 3:
                px, py = self.point(x, bottom)
                self.ui.key_label('SPACE', '물로 불길 끄기', px, py - 15, 45, 12)
        else:
            age = self.room.elapsed - self.room.steam.get(index, -1)
            if age >= .8:
                return
            self.ui.begin()
            for column in range(count):
                x = left + (column + .5) * (right - left) / count
                px, py = self.point(x, y)
                drift = math.sin(column * 2.1 + age * 5) * age * 9
                self.p.draw_circle(px + drift * scale, py + (8 + age * 36) * scale,
                                   round((4 + age * 14) * scale), 194, 227, 222,
                                   round(115 * (1 - age / .8)), filled=True)

    def draw_earth_terrain(self, terrain):
        if terrain.kind == 'floor' and (self.room.quarry or self.room.acquisition and self.room.turret_room):
            self.acquisition_art.bridge(terrain.bounds, 'earth', terrain.remaining / self.room.earth_seconds)
            return
        if (self.room.quarry or self.room.trial) and terrain.kind == 'wall':
            self.quarry_art.wall(terrain)
            return
        left, top, right, bottom = terrain.bounds
        x0, y1 = self.point(left, top)
        x1, y0 = self.point(right, bottom)
        self.ui.begin()
        warning = terrain.remaining < .75 and int(self.room.elapsed * 12) % 2
        color = (163, 124, 87, 190) if warning else (208, 157, 92, 255)
        grout = (131, 91, 57)
        if terrain.kind == 'wall':
            wall_base = (100, 65, 46, 255)
            if not self.room.reference_art:
                wall_base = (85, 57, 57, 255)
                color = (127, 92, 79, 190) if warning else (159, 118, 96, 255)
                grout = (108, 74, 66)
            self.ui.rounded(x0, y0, x1 - x0, y1 - y0 + 17, 4, wall_base)
            y0 += 14
            y1 += 17
        else:
            self.ui.rounded(x0, y0 - 4, x1 - x0, y1 - y0 + 4, 3, (112, 75, 48, 255))
        self.ui.rounded(x0, y0, x1 - x0, y1 - y0, 3, color)
        if terrain.kind == 'wall' and not self.room.reference_art:
            self.p.draw_line(x0 + 4, y1 - 3, x1 - 4, y1 - 3, 203, 157, 123)
        segments = max(1, round(max(right - left, bottom - top) * 1.6))
        for i in range(1, segments):
            if x1 - x0 > y1 - y0:
                x = x0 + (x1 - x0) * i / segments
                self.p.draw_line(x, y0 + 2, x, y1 - 2, *grout)
            else:
                y = y0 + (y1 - y0) * i / segments
                self.p.draw_line(x0 + 2, y, x1 - 2, y, *grout)

    def draw_turret_switch(self):
        room = self.room
        x, y = self.point(*room.turret_room['switch'])
        if not room.turrets_stopped:
            self.connect_image.draw(x, y + 4, 42, 42)
            return
        self.ui.begin()
        self.ui.rounded(x - 22, y - 20, 44, 40, 4, (50, 91, 73, 255))
        self.ui.rounded(x - 16, y - 14, 32, 28, 3, (118, 193, 135, 255))
        self.p.draw_line(x - 7, y, x - 2, y - 5, 40, 79, 63)
        self.p.draw_line(x - 2, y - 5, x + 8, y + 7, 40, 79, 63)

    def draw_stone_gate(self, puzzle, opening):
        left, top, right, bottom = puzzle['gatePixels']
        scale = self.view.reference_scale
        half = self.gate_image.w // 2
        elapsed = self.room.power_gate_time if puzzle is self.room.power_puzzle else self.room.gate_time
        fraction = 1 - elapsed / self.room.gate_open_seconds
        visible = round(half * fraction)
        if not opening:
            x, y = self.view.reference_point((left + right) / 2, (top + bottom) / 2)
            self.gate_image.draw(x, y, (right - left) * scale, (bottom - top) * scale)
        elif visible:
            width = (right - left) * visible / self.gate_image.w
            for src_x, center in ((half - visible, left + width / 2),
                                  (self.gate_image.w - half, right - width / 2)):
                x, y = self.view.reference_point(center, (top + bottom) / 2)
                self.gate_image.clip_draw(src_x, 0, visible, self.gate_image.h,
                                          x, y, width * scale, (bottom - top) * scale)

    def draw_power_floor(self):
        puzzle = self.room.power_puzzle
        x, y = puzzle['switch']
        sx, sy = self.point(x, y)
        color = (255, 193, 82) if self.room.power_connected else (133, 88, 52)
        if not self.room.trial:
            for cx, cy in puzzle['conductors']:
                px, py = self.point(cx, cy)
                self.p.draw_line(px, py, px, sy, *color)
                self.p.draw_line(px, sy, sx, sy, *color)
        gx, gy, gr, gb = puzzle['gate']
        end_x, end_y = self.point((gx + gr) / 2, gb)
        self.p.draw_line(sx, sy, end_x, end_y, *color)
        scale = self.view.reference_scale
        self.connect_image.draw(sx, sy, 47 * scale, 47 * scale)
        if not self.room.power_connected and (not self.room.trial or self.room.branches_open):
            key_x, key_y = (sx+56*scale, sy) if self.room.trial else (sx, sy-34*scale)
            self.ui.key_label('G', '연결', key_x, key_y, 26, size=13)

    def draw_trial_floor(self):
        room = self.room
        trial = room.trial
        self.ui.begin()
        drain = room.gate_time / room.gate_open_seconds
        if 0 < drain < 1:
            self.draw_trial_flow(trial['drainPath'], min(1, drain / .52),
                                 None, (53, 156, 156), (164, 235, 218), 4,
                                 start_progress=max(0, (drain-.3)/.7))
        self.draw_trial_basin(drain)
        self.draw_trial_flow(trial['waterPath'], room.trial_flow(0),
                             (43, 52, 67), (79, 155, 191), (161, 225, 248), 5)
        self.draw_trial_flow(trial['powerPath'], room.trial_flow(1),
                             (85, 61, 58), (188, 130, 63), (255, 222, 135), 3)
        amplitude, _ = trial['laserSweep']
        for start, receiver, row in trial['lasers']:
            for edge in (start, receiver):
                x, low = self.point(edge, row+amplitude)
                _, high = self.point(edge, row-amplitude)
                self.p.draw_rectangle(x-3, low, x+3, high, 74, 54, 56, filled=True)
                self.p.draw_line(x, low, x, high, 151, 110, 93)
        if room.trial_returns == {0} and room.trial_laser_locked and not any(
                t.kind == 'wall' and t.contains(*trial['wallSlot']) for t in room.earth_terrain):
            x, y = self.point(*trial['wallSlot'])
            self.p.draw_rectangle(x-23, y-6, x+23, y+6, 160, 121, 89)
            if math.dist((room.player.x, room.player.y), trial['wallSlot']) < 3:
                self.ui.key_label('R', '흙벽으로 레이저 차단', x, y+28, 22, 13)

    def draw_trial_basin(self, drain):
        left, top, right, bottom = self.room.trial['basin']
        x0, y1 = self.point(left, top)
        x1, y0 = self.point(right, bottom)
        self.p.draw_rectangle(x0, y0, x1, y1, 71, 60, 72, filled=True)
        self.p.draw_rectangle(x0+3, y0+3, x1-3, y1-3, 91, 76, 82, filled=True)
        for divider in range(1, 4):
            y = y0+3+(y1-y0-6)*divider/4
            self.p.draw_line(x0+3, y, x1-3, y, 73, 61, 71)
        if drain >= 1:
            return
        low = y0+3
        high = low+(y1-y0-6)*(1-drain)
        self.p.draw_rectangle(x0+3, low, x1-3, high, 53, 122, 135, filled=True)
        self.p.draw_line(x0+4, high, x1-4, high, 142, 219, 213)
        for i in range(1, 7):
            y = low+(high-low)*i/7
            wave = 5 + 4 * math.sin(self.room.elapsed*4+i)
            self.p.draw_line(x0+8, y, x0+8+wave, y, 113, 188, 181)

    def draw_trial_flow(self, path, progress, base, light, highlight, width, *, start_progress=0):
        links = [(a, b, math.dist(a, b)) for a, b in zip(path, path[1:])]
        total_length = sum(length for _, _, length in links)
        flow_start, flow_end = total_length * start_progress, total_length * progress
        distance = 0.0
        for start, end, length in links:
            x0, y0 = self.point(*start)
            x1, y1 = self.point(*end)
            visible = (max(x0, x1) >= -12 and min(x0, x1) <= self.width+12
                       and max(y0, y1) >= -12 and min(y0, y1) <= self.height+12)
            first = max(0, flow_start - distance)
            last = min(length, flow_end - distance)
            if visible:
                if base is not None:
                    self.p.draw_rectangle(min(x0, x1)-width, min(y0, y1)-width,
                                          max(x0, x1)+width, max(y0, y1)+width, *base, filled=True)
                if last > first:
                    dx, dy = (x1 - x0) / length, (y1 - y0) / length
                    sx, sy = x0 + dx * first, y0 + dy * first
                    ex, ey = x0 + dx * last, y0 + dy * last
                    spread = width - 1
                    self.p.draw_rectangle(min(sx, ex)-spread, min(sy, ey)-spread,
                                          max(sx, ex)+spread, max(sy, ey)+spread, *light, filled=True)
                    spacing = .7
                    offset = first + (self.room.elapsed * 9 - distance - first) % spacing
                    while offset < last:
                        trail = min(offset+.18, last)
                        self.p.draw_line(x0+dx*offset, y0+dy*offset, x0+dx*trail, y0+dy*trail, *highlight)
                        offset += spacing
                    if progress < 1 and flow_end <= distance + length:
                        self.p.draw_circle(ex, ey, width+2, *highlight, filled=True)
            distance += length

    def draw_trial_wheel(self, x, y):
        room = self.room
        sx, sy = self.point(x, y)
        if not (-60 <= sx <= self.width+125 and -110 <= sy <= self.height+24):
            return
        if self.trial_waterwheel is None:
            folder = room.map_path.parent
            spec = json.loads((folder / 'trial-waterwheel.json').read_text(encoding='utf-8'))
            self.trial_waterwheel = self.p.load_image(str(folder / spec['image'])), spec
        image, spec = self.trial_waterwheel
        width, height = spec['frameSize']
        pivot_x, pivot_y = spec['pivot']
        scale = self.view.tile_width / spec['pixelsPerTile']
        opening_frames = spec['openingFrames']
        elapsed = room.trial_wheel_time
        reveal = room.trial_wheel_reveal_seconds
        frame = 0
        if room.trial_wheel_open:
            spin = int((elapsed-reveal) * spec['fps'])
            frame = 1 + opening_frames + spin % spec['activeFrames']
        elif elapsed > 0:
            frame = 1 + int(elapsed / reveal * opening_frames)
        row, column = divmod(frame, spec['columns'])
        left, top, right, _ = room.trial['wheelGate']
        player = room.player
        behind = room.trial_wheel_open and left < player.x < right and top-2.35 < player.y < top
        if behind:
            fade = min(1, (top-player.y)*3, (player.y-top+2.35)*2)
            image.opacify(1-.55*fade)
        image.clip_draw(column*width, image.h-(row+1)*height, width, height,
                        sx+(width/2-pivot_x)*scale, sy+(pivot_y-height/2)*scale,
                        width*scale, height*scale)
        if behind:
            image.opacify(1)
        if room.trial_wheel_open and math.dist((room.player.x, room.player.y), (x, y)) < 2.5:
            self.ui.text('레이저 고정', sx+(width/2-pivot_x)*scale, sy-21*scale, 13, (161, 225, 248))

    def draw_trial_switch(self, index):
        room = self.room
        point = room.trial['switches'][index]
        self.acquisition_art.draw_counterweight_prop('lever', point)
        if index not in room.trial_returns and math.dist((room.player.x, room.player.y), point) <= .9:
            x, y = self.point(*point)
            self.ui.begin()
            self.ui.text('G · 수문 열기' if index == 0 else 'G · 서쪽으로 전력 보내기', x, y+34, 13)

    def trial_layers(self):
        room = self.room
        trial = room.trial
        if self.garden_art is None:
            self.garden_art = GardenArt(self, STAGES[7].parent)
        if self.quarry_art is None:
            self.quarry_art = QuarryArt(self, STAGES[8].parent)
        gates = [gate for i, gate in enumerate(trial['returns']) if i not in room.trial_returns]
        if not room.trial_laser_locked:
            gates.append(trial['serviceGate'])
        for gate in gates:
            yield gate[3], self.garden_art.slide_gate, (self.garden_art.passage_gate, gate, 0)
        if not room.stone_gate_open:
            gate = room.puzzle['gate']
            yield gate[3], self.garden_art.slide_gate, (
                self.garden_art.passage_gate, gate, room.gate_time / room.gate_open_seconds)
        for i, (_, y) in enumerate(trial['switches']):
            yield y, self.draw_trial_switch, (i,)
        wheel_x, wheel_y = trial['waterPath'][-1]
        yield trial['wheelGate'][3], self.draw_trial_wheel, (wheel_x, wheel_y)
        if room.active_lasers:
            for start, stop, y, receiver in room.active_lasers.beams(room.earth_terrain):
                yield y-.3, self.quarry_art.draw_beam, (start, stop, y, receiver)
                if stop != receiver:
                    yield y+.45, self.quarry_art.sprite, ('impact', stop, y, 44, start < receiver)
        else:
            for start, receiver, y in trial['lasers']:
                yield y-.3, self.quarry_art.sprite, ('receiver-cut', start, y, 43)
                yield y-.3, self.quarry_art.sprite, ('receiver-cut', receiver, y, 34)

    def draw_conductor(self, index):
        room = self.room
        x, y = self.point(*room.power_puzzle['conductors'][index])
        scale = self.view.reference_scale
        level = room.power_levels[index]
        target = room.power_targets[index]
        if room.trial:
            if self.trial_conductor_sheet is None:
                self.trial_conductor_sheet = self.p.load_image(str(room.map_path.with_name('trial-conductors.png')))
            sheet = self.trial_conductor_sheet
            width, height = sheet.w//5, sheet.h//len(room.trial['runes'])
            powered = room.conductor_powered(index)
            column = level+1 if powered else 0
            sheet.clip_draw(column*width, sheet.h-(index+1)*height, width, height,
                            x, y+18*scale, width*scale, height*scale)
            if not powered:
                return
        else:
            self.conductor_images[level].draw(x, y+18*scale, 66*scale, 67*scale)
        hit = room.power_hits[index]
        phase = int(room.elapsed * 14) + index * 5
        if level == 0 and not room.trial:
            self.ui.begin()
            brightness = round(90 + 34 * math.sin(room.elapsed * 5 + index * 2))
            self.p.draw_circle(x, y + 25 * scale, max(1, round(2 * scale)),
                               255, 197, 92, brightness, filled=True)
        for terminal, (tx, ty) in enumerate(((-16, 37), (1, 40), (12, 37))):
            if terminal >= level and not (hit and terminal == 0):
                continue
            px, py = x + tx * scale, y + ty * scale
            tick = phase + terminal * 3
            length = (4 + tick % 4 + 24 * hit) * scale
            side = -1 if tick % 2 else 1
            self.draw_electric_arc(px, py, px + side * length, py + length, 2 * scale,
                                   225 if hit or room.power_connected else 155, tick)
        if not room.trial:
            self.ui.text(f'{chr(65 + index)} {level}/{target}', x, y-22*scale, 14)
        if room.power_flash and (not room.trial or index in room.trial_wrong):
            radius = round((14 + 45 * room.power_flash) * scale)
            self.p.draw_circle(x, y + 30 * scale, radius, 255, 232, 143)

    def draw_electric_arc(self, x, y, tx, ty, offset, alpha, phase,
                          *, glow=(77, 155, 255), core=(222, 249, 255)):
        dx, dy = tx - x, ty - y
        length = math.hypot(dx, dy) or 1
        bend = min(offset, length * .3) * (-1 if phase % 2 else 1) / length
        bolt = [(x, y)]
        for fraction, side in ((.25, 1), (.5, -.7), (.75, .5)):
            bolt.append((x + dx * fraction - dy * bend * side,
                         y + dy * fraction + dx * bend * side))
        bolt.append((tx, ty))
        self.ui.begin()
        for (x0, y0), (x1, y1) in zip(bolt, bolt[1:]):
            for spread in (-1, 1):
                self.p.draw_line(x0 + spread, y0, x1 + spread, y1, *glow, alpha // 2)
            self.p.draw_line(x0, y0, x1, y1, *core, alpha)

    def draw_lightning_charge(self, actor, root_x, root_y):
        if actor.falling or not (self.room.lightning_charged or
                                 (self.room.lightning_attack and not actor.attack_emitted)):
            return
        tick = int(self.room.elapsed * 14)
        center_y = root_y + self.unit * .42
        for index in range(3):
            angle = tick * .24 + index * math.tau / 3
            x = root_x + math.cos(angle) * self.unit * .54
            y = center_y + math.sin(angle) * self.unit * .42
            end = angle + .36 + ((tick + index) % 3) * .10
            tx = root_x + math.cos(end) * self.unit * .65
            ty = center_y + math.sin(end) * self.unit * .50
            self.draw_electric_arc(x, y, tx, ty, self.unit * .08, 225, tick + index)

    def draw_lightning(self):
        alpha = min(255, round(self.room.lightning_time * 1600))
        points = [self.point(x, y, self.unit * .5) for x, y in self.room.lightning_path]
        phase = int(self.room.lightning_time * 36)
        for (x, y), (tx, ty) in zip(points, points[1:]):
            self.draw_electric_arc(x, y, tx, ty, 9, alpha, phase)

    def draw_plate(self):
        x, y = self.point(*self.room.puzzle['plate'])
        scale = self.view.reference_scale
        reset = self.room.puzzle.get('reset')
        if reset:
            if self.room.trial:
                self.acquisition_art.draw_counterweight_prop('socket', self.room.puzzle['plate'])
                self.acquisition_art.draw_counterweight_prop('lever', reset)
            elif self.room.stage >= 9 or self.room.data.get('requiredBridge'):
                self.connect_image.draw(x, y, 38 * scale, 38 * scale)
                rx, ry = self.point(*reset)
                self.connect_image.draw(rx, ry, 24 * scale, 24 * scale)
            elif self.room.puzzle.get('centeredSlide'):
                self.acquisition_art.draw_counterweight_prop('lever', reset)
            if not self.room.plate_pressed and math.hypot(self.room.player.x - reset[0],
                                                         self.room.player.y - reset[1]) <= .9:
                rx, ry = self.point(*reset)
                self.ui.text('G · 돌 복귀', rx, ry + 30, 13)
            return
        self.ui.begin()
        border = (171, 251, 133, 255) if self.room.plate_pressed else (152, 191, 129, 255)
        self.ui.rounded(x - 23 * scale, y - 20 * scale, 46 * scale, 40 * scale, 5, border)
        self.ui.rounded(x - 20 * scale, y - 17 * scale, 40 * scale, 34 * scale, 4, (58, 83, 70, 255))
        self.p.draw_circle(x, y, 8 * scale, *border[:3])

    def draw_puzzle_block(self):
        if self.room.puzzle.get('centeredSlide'):
            self.acquisition_art.draw_counterweight_prop('stone', self.room.block)
            return
        x, y = self.point(*self.room.block)
        scale = self.view.reference_scale
        self.block_image.draw(x, y + 6 * scale, 57 * scale, 39 * scale)

    def fade_walls_over_puzzle_block(self, layers):
        view = self.view
        x, y = self.room.block
        reference = self.room.reference_art or {}
        cover_bounds = dict(zip(map(tuple, reference.get('coverPixels', ())), reference.get('cover', ())))
        for index, (depth, draw, args) in enumerate(layers):
            if draw == view.draw_wall:
                bounds = args[0].wall_bounds
            elif draw == view.draw_reference_cover:
                bounds = cover_bounds.get(tuple(args[0]))
                if bounds is None:
                    continue
            else:
                continue
            left, top, right, _ = bounds
            # 평형추 아랫면의 폭은 .98칸이고, 칸 중앙에 놓일 때는 .01칸이 남는다.
            if 0 < top - y <= .51 and left < x + .49 and x - .49 < right:
                layers[index] = depth, draw, (*args, 100)

    def exit_visual(self):
        return self.room.exit_open, (116, 202, 178)

    def draw_reference_exit(self):
        x0, y0, x1, y1 = self.room.reference_art['doorPixels']
        center = (x0 + x1) / 2
        opened, color = self.exit_visual()
        if opened:
            self.ui.begin()
            for row in range(21):
                left, y = self.view.reference_point(x0 + 2, y1 - row)
                right, _ = self.view.reference_point(x1 - 2, y1 - row)
                self.p.draw_line(left, y, right, y, *color, 110 - row * 5)
            exit_point = self.room.data['plannedExit']
            self.view.draw_exit_marker(exit_point['x'], exit_point['y'], True)
            return
        radius = (x1 - x0) / 2
        for offset in (-21, -14, -7, 0, 7, 14, 21):
            top = y0 + radius - math.sqrt(radius ** 2 - offset ** 2)
            x, upper = self.view.reference_point(center + offset, top + 2)
            _, bottom = self.view.reference_point(center + offset, y1 - 1)
            self.p.draw_line(x, bottom, x, upper, 178, 138, 94)
        for row in (y1 - 37, y1 - 14):
            left, y = self.view.reference_point(x0 + 4, row)
            right, _ = self.view.reference_point(x1 - 4, row)
            self.p.draw_line(left, y, right, y, 164, 126, 88)

    def draw_exit(self):
        if self.room.reference_art and 'doorWallPixels' in self.room.reference_art:
            x0, y0, x1, y1 = self.room.reference_art['doorPixels']
            scale = self.view.reference_scale
            left, top = self.view.reference_point(x0, y0)
            right, bottom = self.view.reference_point(x1, y1)
            self.ui.begin()
            self.ui.rounded(left - 4 * scale, bottom, right - left + 8 * scale,
                            top - bottom + 4 * scale, 26 * scale, (113, 99, 130, 255))
            self.ui.rounded(left, bottom, right - left, top - bottom,
                            24 * scale, (25, 21, 30, 255))
            self.p.draw_rectangle(left, bottom, right, bottom + 25 * scale,
                                  25, 21, 30, filled=True)
        if self.room.guardian:
            self.guardian_art.exit()
            return
        if self.room.trial:
            self.garden_art.exit(float(self.room.exit_open))
            return
        if self.room.garden:
            self.garden_art.exit()
            return
        if self.room.quarry:
            self.garden_art.exit(self.room.quarry.exit_time/self.room.quarry.exit_seconds,
                                 self.quarry_art.exit_grille)
            return
        if self.room.reference_art:
            self.draw_reference_exit()
            return
        exit_point = self.room.data['plannedExit']
        opened, color = self.exit_visual()
        x, y = self.point(exit_point['x'], self.room.data['floorRegions'][0]['y'])
        self.ui.begin()
        p = self.p

        def arch(radius, spring, color):
            p.draw_rectangle(x - radius, y, x + radius, y + spring, *color, filled=True)
            for row in range(1, radius + 1):
                span = round(math.sqrt(radius * radius - row * row))
                p.draw_line(x - span, y + spring + row, x + span, y + spring + row, *color)

        arch(30, 52, (45, 34, 52))
        arch(28, 51, (128, 103, 127))
        arch(23, 51, (94, 74, 101))
        arch(20, 50, (25, 20, 34))
        for side in (-1, 1):
            for height in (15, 29, 43):
                p.draw_line(x + side * 21, y + height, x + side * 28, y + height, 58, 44, 65)
            for angle in (24, 52):
                angle_rad = math.radians(angle)
                p.draw_line(x + side * 22 * math.cos(angle_rad), y + 51 + 22 * math.sin(angle_rad),
                            x + side * 28 * math.cos(angle_rad), y + 51 + 28 * math.sin(angle_rad), 58, 44, 65)
        p.draw_rectangle(x - 5, y + 73, x + 5, y + 81, 155, 124, 136, filled=True)
        self.ui.diamond(x, y + 77, 3, (172, 227, 196) if opened else (210, 168, 110))

        lift = 1 if opened else self.room.powered_door_lift
        if lift:
            for row in range(27):
                strength = (27 - row) / 27
                span = round(19 - row * .16)
                p.draw_line(x - span, y + row, x + span, y + row, *color, round(120 * strength * lift))
        if opened:
            p.draw_rectangle(x - 30, y - 5, x + 30, y, 82, 66, 91, filled=True)
            p.draw_line(x - 24, y - 1, x + 24, y - 1, 157, 209, 179)
            self.view.draw_exit_marker(exit_point['x'], exit_point['y'], opened)
        else:
            risen = round(55 * lift * lift * (3 - 2 * lift))
            if risen < 55:
                for dx in (-14, -7, 0, 7, 14):
                    p.draw_line(x + dx, y + 1 + risen, x + dx, y + 56, 117, 93, 83)
            for height in (15 + risen, 40 + risen):
                if height <= 56:
                    p.draw_line(x - 19, y + height, x + 19, y + height, 157, 125, 94)
            p.draw_rectangle(x - 30, y - 5, x + 30, y, 82, 66, 91, filled=True)

    def start_trial_drain_cutscene(self):
        room = self.room
        progress = room.gate_time / room.gate_open_seconds
        remaining = (1-progress) * room.trial['drainSeconds']
        self.trial_cutscene = ('drain', room.elapsed + remaining + .65)

    def draw_trial_cutscene(self):
        room = self.room
        if not self.trial_cutscene or self.paused or room.outcome or room.debug_cleared:
            return
        kind, until = self.trial_cutscene
        if room.elapsed >= until:
            return
        p = self.p
        viewport = p.SDL_Rect(28, 268, 424, 238)
        if kind == 'drain':
            left, top, right, _ = room.trial['basin']
            _, bend_y = room.trial['drainPath'][1]
            focus = (left+right)/2+.45, (top+bend_y)/2
            title, zoom = '서쪽 수로 배수', 1.10
        else:
            x, y = room.trial['waterPath'][-1]
            focus = x-.55, y-1.37
            title, zoom = '동쪽 물레방아 작동', 1.20
            viewport.x = self.width-viewport.x-viewport.w

        self.draw_inset(focus, zoom, viewport, title)

    def draw_inset(self, focus, zoom, viewport, title):
        panel_bottom = self.height-viewport.y-viewport.h-8
        self.ui.begin()
        self.ui.panel(viewport.x-8, panel_bottom, viewport.w+16, viewport.h+43, accent=True)
        self.ui.text(title, viewport.x+viewport.w/2, self.height-viewport.y+17, 16)
        self.draw_world_from(focus, zoom, viewport)

    def draw_world_from(self, focus, zoom, viewport=None, *, screen_point=None):
        p = self.p
        renderer = p.pico2d.renderer
        clip = None
        if viewport is not None:
            old_clip = p.SDL_Rect()
            if p.SDL_RenderIsClipEnabled(renderer):
                clip = ctypes.byref(old_clip)
                p.SDL_RenderGetClipRect(renderer, clip)
            if p.SDL_RenderSetClipRect(renderer, ctypes.byref(viewport)) < 0:
                return
        # 같은 월드를 컷씬 위치에서 한 번 더 그리고 메인 카메라를 복원한다.
        view = self.view
        origin = view.origin
        scale, tile_width, tile_height = view.reference_scale, view.tile_width, view.tile_height
        try:
            view.reference_scale = scale*zoom
            view.tile_width, view.tile_height = tile_width*zoom, tile_height*zoom
            if screen_point is not None:
                px, py = view.project(*focus)
                view.origin = round(screen_point[0]-px), round(self.height-screen_point[1]-py)
            elif viewport is None:
                view.follow(*focus)
            else:
                px, py = view.project(*focus)
                view.origin = (
                    round(viewport.x+viewport.w/2-px), round(viewport.y+viewport.h/2-py))
            self.draw_world()
        finally:
            view.origin = origin
            view.reference_scale, view.tile_width, view.tile_height = scale, tile_width, tile_height
            if viewport is not None:
                p.SDL_RenderSetClipRect(renderer, clip)

    def draw_cutscene_world(self, focus, screen_point, zoom):
        p = self.p
        renderer = p.pico2d.renderer
        target = p.SDL_GetRenderTarget(renderer)
        # 바닥 캐시와 월드 오브젝트를 같은 비율로 확대한다.
        if p.SDL_SetRenderTarget(renderer, self.cutscene_background) != 0:
            raise RuntimeError('원소 습득 컷씬 화면을 열 수 없습니다.')
        try:
            p.clear_canvas()
            self.draw_world_from(focus, 1, screen_point=screen_point)
        finally:
            p.SDL_SetRenderTarget(renderer, target)
        x, y = screen_point
        destination = p.SDL_Rect(round(x * (1 - zoom)), round((self.height - y) * (1 - zoom)),
                                 round(self.width * zoom), round(self.height * zoom))
        p.SDL_RenderCopy(renderer, self.cutscene_background, None, ctypes.byref(destination))

    def draw(self, present=True):
        p = self.p
        p.clear_canvas()
        if self.scene == 'title':
            draw_title(self)
        elif self.room.stage == 0:
            self.draw_world()
            self.guardian_art.prologue()
            if self.paused:
                self.ui.modal(self.width,self.height,self.paused,self.menu,self.menu_index,None,0)
        elif self.ending:
            self.draw_world()
            self.guardian_art.ending(self.ending_elapsed)
        elif self.ingest_cutscene:
            self.ingest_cutscene.draw(self)
            if self.paused:
                self.ui.modal(self.width,self.height,self.paused,self.menu,self.menu_index,self.room.outcome,self.room.stage)
        elif self.room.guardian and self.room.guardian.collapsing:
            self.guardian_art.defeat_camera()
            if self.paused:
                self.ui.modal(self.width,self.height,self.paused,self.menu,self.menu_index,None,self.room.stage)
        else:
            guardian = self.room.guardian
            if guardian and guardian.summoning:
                self.guardian_art.camera()
            else:
                self.draw_world()
            self.draw_trial_cutscene()
            if guardian and not self.paused and not self.room.outcome and self.guardian_art.show_exit_inset():
                viewport = p.SDL_Rect((self.width-424)//2,118,424,238)
                self.draw_inset((15,2.4),1.05,viewport,'북쪽 성문 개방')
            self.draw_hud()
            self.acquisition_art.draw_prompt()
            if guardian:
                self.guardian_art.status()
                self.guardian_art.reward_prompt()
            if self.paused or (self.room.outcome and self.stage_fade_out is None):
                self.ui.modal(self.width,self.height,self.paused,self.menu,self.menu_index,self.room.outcome,self.room.stage)
        if self.orb_mixer:
            self.orb_mixer.draw()
        if self.scene == 'play' and self.fading_stage:
            if self.stage_fade_out is not None:
                progress = smoothstep(self.stage_fade_out / self.stage_fade_out_seconds)
            else:
                progress = 1 - smoothstep(self.stage_fade_in / self.stage_fade_in_seconds)
            self.ui.begin()
            p.draw_rectangle(0, 0, self.width-1, self.height-1, 0, 0, 0, round(255 * progress), filled=True)
        if present:
            p.update_canvas()

    def draw_world(self):
        p = self.p
        background = self.acquisition_art.draw_cliff_fog if self.room.stage in (1, 4, 5) else None
        self.view.draw_ground(background)
        self.acquisition_art.draw()
        if self.room.quarry and self.room.permanent_bridge:
            self.acquisition_art.bridge(self.room.permanent_bridge, 'stone')
        if self.room.guardian:
            self.guardian_art.floor()
        for terrain in self.room.earth_terrain:
            if terrain.kind == 'floor':
                self.draw_earth_terrain(terrain)
        if self.room.turret_room:
            self.draw_turret_switch()
        if self.room.puzzle and not self.room.quarry:
            self.draw_plate()
        if self.room.quarry:
            if self.quarry_art is None:
                self.quarry_art = QuarryArt(self, self.room.map_path.parent)
            if self.garden_art is None:
                self.garden_art = GardenArt(self, STAGES[7].parent)
        if self.room.garden:
            if self.garden_art is None:
                self.garden_art = GardenArt(self, self.room.map_path.parent)
            self.garden_art.wires()
        elif self.room.sluice:
            for key, active, instruction in (('wheel', self.room.sluice_wheel, 'G · 손잡이'),
                                              ('pump', self.room.sluice_pump, '번개 Space · 펌프')):
                x, y = self.point(*self.room.sluice[key])
                self.connect_image.draw(x, y, 35, 35)
                self.ui.text('작동 완료' if active else instruction, x, y+26, 13)
        if self.room.power_puzzle:
            self.draw_power_floor()
        if self.room.trial:
            self.draw_trial_floor()
        exit_point = self.room.data['plannedExit']
        layers = [(depth, self.view.draw_wall, (wall,)) for depth, wall in self.view.walls]
        if self.room.reservoir:
            layers.append((self.room.reservoir['origin'][1], self.acquisition_art.draw_cistern, ()))
        if self.room.forge:
            layers.append((self.room.forge['origin'][1], self.acquisition_art.draw_forge, ()))
        if self.room.windmill:
            layers.append((self.room.windmill['base'][3], self.acquisition_art.draw_windmill, ()))
        if self.room.turret_room:
            layers.extend((y, self.acquisition_art.draw_turret, (index,))
                          for index, (_, y) in enumerate(self.room.turret_room['emitters']))
        if self.room.capacitor:
            layers.append((self.room.sources[-1].y, self.acquisition_art.draw_capacitor, ()))
            if not self.room.learned_room_element:
                layers.extend((bounds[3], self.acquisition_art.draw_bulkhead, (bounds, front, pillar))
                              for bounds, front, pillar in self.acquisition_art.bulkhead_sections())
        layers.append((exit_point['y'], self.draw_exit, ()))
        layers.extend((terrain.bounds[3], self.draw_earth_terrain, (terrain,))
                      for terrain in self.room.earth_terrain if terrain.kind == 'wall')
        if self.room.reference_art:
            origin_y = self.room.reference_art['originPixels'][1]
            unit = self.room.reference_art['pixelsPerTile']
            for rect in self.room.reference_art['coverPixels']:
                layers.append(((rect[3] - origin_y) / unit, self.view.draw_reference_cover, (rect,)))
            for rect in self.room.reference_art.get('foregroundWallPixels', []):
                layers.append(((rect[1] - origin_y) / unit, self.view.draw_reference_cover, (rect,)))
        if self.room.garden:
            layers.extend(self.garden_art.layers())
        elif not self.room.sluice_open:
            layers.append((self.room.sluice['gate'][3], self.draw_stone_gate, (self.room.sluice, False)))
        if self.room.puzzle:
            if not self.room.debug_cleared:
                self.fade_walls_over_puzzle_block(layers)
                layers.append((self.room.block[1], self.draw_puzzle_block, ()))
            if self.room.quarry:
                layers.extend(self.quarry_art.layers())
            elif not self.room.trial and not self.room.acquisition and (not self.room.stone_gate_open
                    or self.room.data.get('requiredBridge') and not self.room.bridge_crossed):
                layers.append((self.room.puzzle['gate'][3], self.draw_stone_gate,
                               (self.room.puzzle, self.room.plate_pressed and
                                (not self.room.data.get('requiredBridge') or self.room.bridge_crossed))))
        if self.room.power_puzzle:
            puzzle = self.room.power_puzzle
            layers.extend((y, self.draw_conductor, (i,)) for i, (_, y) in enumerate(puzzle['conductors']))
            if not self.room.power_gate_open:
                layers.append((puzzle['gate'][3], self.draw_stone_gate, (puzzle, self.room.power_connected)))
        if self.room.trial:
            layers.extend(self.trial_layers())
        if self.room.guardian:
            layers.extend(self.guardian_art.layers())
        if not self.room.vine_open:
            gate = self.room.vine_gate
            layers.append((gate['y'] + gate['height'], self.draw_vine, (gate, self.room.vine_time)))
        gate = self.room.conductor_vine
        if gate and self.room.conductor_vine_time < gate['burnDuration']:
            layers.append((gate['y'] + gate['height'], self.draw_vine, (gate, self.room.conductor_vine_time)))
        layers.extend((bounds[3], self.draw_fire_barrier, (index,))
                      for index, bounds in enumerate(self.room.fire_barriers))
        if not self.ingest_cutscene and self.room.player.active:
            layers.append((self.room.player.y, self.draw_actor, (self.room.player,)))
        if not self.room.guardian:
            layers.extend((a.y, self.draw_actor, (a,)) for a in self.room.enemies if a.active)
        scene_source = self.ingest_cutscene.source if self.ingest_cutscene else None
        layers.extend((s.y, self.draw_source, (s,)) for s in self.room.sources
                      if s.phase not in ('sealed', 'consumed') and s is not scene_source)
        layers.extend((s.y, self.draw_shot, (s,)) for s in self.room.projectiles)
        for _, draw_item, args in sorted(layers, key=lambda layer: layer[0]):
            draw_item(*args)
        if self.room.quarry:
            self.quarry_art.hints()
        if self.room.lightning_time:
            self.draw_lightning()
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

    def release(self):
        self.set_background_music(None)
        self.set_ambience(None)
        self.set_mechanism_sounds((None, None))
        if self.sounds:
            self.p.Mix_HaltChannel(-1)
            self.sounds.clear()
        # SDL 종료 전에 텍스처를 해제한다.
        self.ui.release()
        self.acquisition_art.images.clear()
        self.acquisition_art.spike_props.clear()
        self.acquisition_art.waterworks.clear()
        self.acquisition_art.forge_props.clear()
        self.acquisition_art.wind_props.clear()
        self.acquisition_art.quarry_props = None
        self.acquisition_art.turret_image = None
        self.acquisition_art.powerstation_props = None
        self.images.clear()
        self.transformation_effects.sheets.clear()
        self.p.SDL_DestroyTexture(self.cutscene_background)
        self.view.release()
        self.shot_images.clear()
        self.source_images.clear()
        self.conductor_images.clear()
        self.trial_conductor_sheet = None
        self.connect_image = self.flame_image = None
        self.vine_image = self.block_image = self.gate_image = None
        self.garden_art = self.quarry_art = self.guardian_art = None
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
