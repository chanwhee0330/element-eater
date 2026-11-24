"""유적 분위기의 HUD. 글꼴 실측과 화면 중심을 기준으로 배치한다."""
import ctypes
import os
import math
from .elements import ELEMENTS, NAMES
from pathlib import Path


class GameUI:
    ink = (28, 39, 32)
    cream = (234, 225, 204)
    muted = (173, 185, 157)
    gold = (171, 149, 99)
    line = (112, 123, 92)

    def __init__(self, p, portrait, orb_icons):
        self.p, self.portrait, self.orb_icons = p, portrait, orb_icons
        bundled = Path(p.__file__).parent / 'data/ConsolaMalgun.ttf'
        system_font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/malgun.ttf'
        path = system_font if system_font.is_file() else bundled
        self.fonts = {n: p.load_font(str(path), n) for n in (10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 26)}
        self.metrics = {}
        self.minimap_cache = None
        self.hp_trail = 100
        self.last_time = 0

    def begin(self):
        self.p.SDL_SetRenderDrawBlendMode(self.p.pico2d.renderer, self.p.SDL_BLENDMODE_BLEND)

    def measure(self, value, size):
        font = self.fonts[size]
        key = size, value
        if key not in self.metrics:
            width, height = ctypes.c_int(), ctypes.c_int()
            if self.p.TTF_SizeUTF8(font.font, value.encode('utf-8'), ctypes.byref(width), ctypes.byref(height)) != 0:
                raise RuntimeError('UI 글꼴 크기 측정 실패')
            self.metrics[key] = width.value
        return self.metrics[key]

    def text(self, value, x, y, size=14, color=None, align='center'):
        font = self.fonts[size]
        width = self.measure(value, size)
        left = x-width/2 if align == 'center' else x-width if align == 'right' else x
        font.draw(round(left), round(y), value, color or self.cream)

    def key_label(self, key, label, cx, cy, key_width, size=15, disabled=False):
        text_width = self.measure(label, size)
        left = cx-(key_width+14+text_width)/2
        self.keycap(key, left+key_width/2, cy, key_width, disabled=disabled)
        text_x = left+key_width+14+text_width/2
        self.text(label, text_x, cy+1, size, (131, 130, 112) if disabled else self.cream)
        return text_x

    def rounded(self, x, y, width, height, radius, color):
        x, y, width, height = round(x), round(y), round(width), round(height)
        if width <= 0 or height <= 0:
            return
        radius = max(0, min(round(radius), width//2, height//2))
        p = self.p
        if not radius:
            p.draw_rectangle(x, y, x+width-1, y+height-1, *color, filled=True)
            return
        # 가운데는 한 번에 채우고, 반투명 모서리와 겹치지 않게 그린다.
        if height > 2*radius:
            p.draw_rectangle(x, y+radius, x+width-1, y+height-radius-1, *color, filled=True)
        for row in range(radius):
            dy = radius-row-.5
            inset = math.ceil(radius-math.sqrt(radius*radius-dy*dy))
            p.draw_line(x+inset, y+row, x+width-1-inset, y+row, *color)
            other = y+height-1-row
            p.draw_line(x+inset, other, x+width-1-inset, other, *color)

    def panel(self, x, y, width, height, accent=False, radius=9):
        self.rounded(x, y-4, width, height, radius, (8, 9, 8, 125))
        self.rounded(x, y, width, height, radius, (*self.gold, 180) if accent else (*self.line, 165))
        self.rounded(x+1, y+1, width-2, height-2, radius-1, (*self.ink, 244))
        self.p.draw_line(x+radius+3, y+height-2, x+width-radius-4, y+height-2, 188, 171, 126, 40)

    def diamond(self, x, y, radius=3, color=None):
        color = color or self.gold
        radius = round(radius)
        for dy in range(-radius, radius+1):
            half = radius-abs(dy)
            self.p.draw_line(x-half, y+dy, x+half, y+dy, *color)

    def orb_socket_glow(self, x, y, radius, color):
        for spread, alpha in ((9, 12), (6, 19), (3, 32)):
            self.p.draw_circle(x, y, radius+spread, *color, alpha, filled=True)

    def keycap(self, text, cx, cy, width=40, disabled=False):
        color = (91, 88, 75) if disabled else (164, 148, 109)
        self.rounded(cx-width/2, cy-12, width, 25, 5, (*color, 170))
        self.rounded(cx-width/2+1, cy-10, width-2, 22, 4, (48, 61, 47, 255))
        self.text(text, cx, cy+1, 10, color if disabled else (225, 210, 173))

    def portrait_badge(self, cx, cy, radius=22):
        p = self.p
        p.draw_circle(cx, cy-2, radius+2, 9, 11, 9, 140, filled=True)
        p.draw_circle(cx, cy, radius+1, *self.gold, filled=True)
        p.draw_circle(cx, cy, radius, 48, 49, 37, filled=True)
        p.draw_circle(cx, cy, radius-3, 62, 65, 45, filled=True)
        # 원본 스프라이트의 투명 여백까지 고정하여 별도 원화를 만들지 않는다.
        self.portrait.clip_draw(0, 384, 128, 128, cx, cy+3, radius*2.2, radius*2.2)

    def enemy_health(self, actor, x, y, offset=62):
        self.begin()
        y += offset
        self.rounded(x-23, y-3, 46, 7, 3, (15, 17, 15, 240))
        fill = 42*max(0, actor.hp)/actor.max_hp
        if fill > 0:
            self.rounded(x-21, y-1, fill, 3, 1, (190, 106, 87, 255))
        self.rounded(x-23, y+7, 46, 16, 4, (25, 25, 22, 165))
        self.text(f'{actor.hp} / {actor.max_hp}', x, y+15, 11, (239, 229, 208))
        if actor.element in ('fire', 'wind'):
            label, color = ('불 · 약점 물', (226,182,146)) if actor.element == 'fire' else ('바람 · 약점 불', (175,214,159))
            self.rounded(x-46,y+25,92,16,4,(25,25,22,170))
            self.text(label,x,y+33,10,color)

    def minimap(self, room, width, top):
        columns, rows = room.data['columns'], room.data['rows']
        tile_ids = room.data['tileIds']
        scale = min(5, 110 / max(columns, rows))
        map_w, map_h = round(columns * scale), round(rows * scale)
        x, y = width - 33 - map_w, top - 91 - map_h
        self.panel(x - 8, y - 25, map_w + 16, map_h + 33)
        self.p.draw_rectangle(x, y, x + map_w, y + map_h, 18, 23, 23, filled=True)
        # 지형은 그대로이므로 SDL용 사각형 배열을 재사용한다. 표식만 매 프레임 갱신한다.
        key = room.map_path, width, top, self.p.pico2d.canvas_height
        if self.minimap_cache is None or self.minimap_cache[0] != key:
            shades = {tile_ids['wall']: (75, 76, 74), tile_ids['spikes']: (157, 93, 96)}
            groups = {}
            for row, tiles in enumerate(room.data['tiles']):
                for col, tile in enumerate(tiles):
                    if tile == tile_ids['pit']:
                        continue
                    left = round(x + col * scale)
                    bottom = round(y + map_h - (row + 1) * scale)
                    screen_top = int(key[3] - bottom - scale)
                    color = shades.get(tile, (122, 116, 128))
                    groups.setdefault(color, []).append(self.p.SDL_Rect(left, screen_top, int(scale), int(scale)))
            batches = [(color, (self.p.SDL_Rect * len(rects))(*rects)) for color, rects in groups.items()]
            self.minimap_cache = key, batches
        renderer = self.p.pico2d.renderer
        for color, batch in self.minimap_cache[1]:
            self.p.SDL_SetRenderDrawColor(renderer, *color, 255)
            self.p.SDL_RenderFillRects(renderer, batch, len(batch))
        exit_point = room.data['plannedExit']
        exit_x, exit_y = room.final_reward or (exit_point['x'], exit_point['y'])
        self.diamond(x + exit_x * scale, y + map_h - exit_y * scale,
                     3, (168, 207, 155) if room.exit_open else (214, 176, 104))
        player = room.player
        self.p.draw_circle(x + player.x * scale, y + map_h - player.y * scale, 3, 240, 233, 197, filled=True)
        self.text(f'{columns} × {rows}', x + map_w / 2, y - 13, 10, self.muted)

    def hud(self, room, width, height):
        self.begin()
        cx = width / 2
        top = height - 20
        self.panel(20, top - 62, 240, 62)
        self.text('체력', 36, top - 17, 13, self.muted, 'left')
        self.text(f'{room.player.hp} / {room.player.max_hp}', 244, top - 17, 14, self.cream, 'right')
        bx, by, bw = 36, top - 47, 208
        delta = max(0, min(.1, room.elapsed - self.last_time))
        self.last_time = room.elapsed
        self.hp_trail = max(room.player.hp, self.hp_trail - delta * 50)
        self.rounded(bx, by, bw, 11, 5, (56, 65, 51, 255))
        self.rounded(bx, by, bw * self.hp_trail / room.player.max_hp, 11, 5, (159, 139, 87, 255))
        self.rounded(bx, by, bw * room.player.hp / room.player.max_hp, 11, 5, (181, 208, 113, 255))

        self.panel(cx - 122, top - 56, 244, 56, accent=True)
        name = room.data['name']
        self.text(f'{room.stage:02d} · {name}', cx, top - 27, 20)
        if not room.guardian:
            self.panel(width - 180, top - 62, 160, 62)
            self.text('남은 적', width - 100, top - 16, 11, self.muted)
            self.text(f'{room.remaining_enemies} / {len(room.enemies)}', width - 100, top - 39, 18)
        self.minimap(room, width, top+82 if room.guardian else top)

        self.panel(20, 16, 204, 67)
        self.portrait_badge(53, 49, 21)
        mixed = room.guardian and room.guardian.reward_tasted
        self.text('엘리먼트 마스터' if mixed else NAMES[room.selected], 88, 59, 16, align='left')
        learned = [element for element in ELEMENTS if room.inventory[element]]
        held = len(learned)
        summary = '다섯 원소 결합' if mixed else f'배운 원소 {held}종' if held else '배운 원소 없음'
        self.text(summary, 88, 36, 11, self.muted, 'left')

        if held:
            slot_width = 60
            dock_width = max(118, slot_width * held + 20)
            dock_left = cx - dock_width / 2 - 26
            self.panel(dock_left, 16, dock_width, 82)
            for index, element in enumerate(learned):
                x = dock_left + (dock_width - slot_width * held) / 2 + index * slot_width
                if element == room.selected:
                    self.rounded(x + 2, 37, slot_width - 4, 54, 5, (135, 141, 81, 94))
                elif index:
                    self.p.draw_line(x, 44, x, 85, *self.line, 122)
                self.orb_icons[element].draw(x + slot_width / 2, 72, 36, 36)
                self.text(NAMES[element], x + slot_width / 2, 47, 12)
            self.text('Q / E  원소 선택', dock_left + dock_width / 2, 28, 11, self.muted)

        controls_left = width - 304
        self.panel(controls_left, 16, 284, 67)
        charged = room.lightning_charged or (room.lightning_attack and not room.player.attack_emitted)
        attack = f'{NAMES[room.selected]} 공격' if room.selected != 'neutral' else '기본 공격'
        if mixed:
            attack = '혼합 공격'
        self.key_label('SPACE', '연쇄 번개' if charged else attack, controls_left + 77, 60, 44, 12)
        water = room.selected == 'water'
        skills = {'water': '자가 회복', 'wind': '돌풍', 'earth': '지형 생성', 'lightning': '번개 충전'}
        skill = '충전 중' if charged else skills.get(room.selected, '스킬 없음')
        skill_ready = room.selected in skills and (not water or room.player.hp < room.player.max_hp)
        self.key_label('R', skill, controls_left + 217, 60, 24, 12, disabled=not skill_ready)
        ready = 1 - min(1, room.player.attack_cooldown / room.tuning.player_interval)
        self.rounded(controls_left + 18, 41, 118, 3, 1, (63, 73, 55, 255))
        self.rounded(controls_left + 18, 41, 118 * ready, 3, 1, (173, 191, 117, 255))
        self.text('W ↑  A ←  S ↓  D →   ·   Esc  메뉴', controls_left + 142, 29, 10, self.muted)

    def modal(self, width, height, paused, menu, selected, outcome, stage=1):
        self.begin()
        p, cx, cy = self.p, width/2, height/2
        p.draw_rectangle(0, 0, width, height, 10, 10, 8, 150, filled=True)
        if paused:
            self.panel(cx-218, cy-210, 436, 420, accent=True, radius=14)
            self.text('PAUSED', cx, cy+169, 10, self.gold)
            self.text('일시정지', cx, cy+135, 26)
            p.draw_line(cx-142, cy+102, cx+142, cy+102, *self.line)
            self.diamond(cx, cy+102, 3)
            for i, item in enumerate(menu):
                y = cy+50-i*54
                if i == selected:
                    self.rounded(cx-158, y-23, 316, 46, 7, (106, 91, 58, 90))
                    self.diamond(cx-141, y, 3)
                    self.diamond(cx+141, y, 3)
                self.text(item, cx, y, 16, self.cream if i == selected else self.muted)
            self.text('W / S  선택     Enter  확인     Esc  돌아가기', cx, cy-177, 11, self.muted)
        else:
            self.panel(cx-218, cy-123, 436, 246, accent=True, radius=14)
            if outcome == 'clear':
                subtitle, title = ('ELEMENT EATER', '게임 클리어') if stage == 10 else (
                    f'ROOM {stage:02d} COMPLETE',f'{stage}번 방 클리어')
            else:
                subtitle, title = 'TRY AGAIN', '쓰러졌습니다'
            self.text(subtitle,cx,cy+89,10,self.gold)
            self.text(title,cx,cy+48,26)
            p.draw_line(cx-118, cy+12, cx+118, cy+12, *self.line)
            self.diamond(cx, cy+12, 3)
            self.rounded(cx-141, cy-66, 282, 44, 7, (106, 91, 58, 90))
            self.text('Enter  현재 방 다시 시작', cx, cy-44, 15)
            self.text('Esc  메뉴', cx, cy-99, 11, self.muted)

    def release(self):
        self.portrait = self.orb_icons = None
