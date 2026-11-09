"""유적 분위기의 HUD. 글꼴 실측과 화면 중심을 기준으로 배치한다."""
import ctypes
import os
import math
from .elements import NAMES
from pathlib import Path


class GameUI:
    ink = (28, 29, 26)
    cream = (234, 225, 204)
    muted = (163, 157, 139)
    gold = (171, 149, 99)
    line = (102, 95, 77)

    def __init__(self, p, portrait):
        self.p, self.portrait = p, portrait
        bundled = Path(p.__file__).parent / 'data/ConsolaMalgun.ttf'
        system_font = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/malgun.ttf'
        path = system_font if system_font.is_file() else bundled
        self.fonts = {n: p.load_font(str(path), n) for n in (10, 11, 12, 13, 14, 15, 16, 18, 20, 24, 26)}
        self.metrics = {}
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
        # 반투명 도형을 중첩하지 않아 모서리가 얼룩지지 않도록 한 줄씩 채운다.
        for row in range(height):
            dy = radius-row-.5 if row < radius else row-(height-radius)+.5 if row >= height-radius else 0
            inset = math.ceil(radius-math.sqrt(max(0, radius*radius-dy*dy))) if dy else 0
            p.draw_line(x+inset, y+row, x+width-1-inset, y+row, *color)

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

    def keycap(self, text, cx, cy, width=40, disabled=False):
        color = (91, 88, 75) if disabled else (164, 148, 109)
        self.rounded(cx-width/2, cy-12, width, 25, 5, (*color, 170))
        self.rounded(cx-width/2+1, cy-10, width-2, 22, 4, (41, 41, 34, 255))
        self.text(text, cx, cy+1, 10, color if disabled else (225, 210, 173))

    def portrait_badge(self, cx, cy, radius=22):
        p = self.p
        p.draw_circle(cx, cy-2, radius+2, 9, 11, 9, 140, filled=True)
        p.draw_circle(cx, cy, radius+1, *self.gold, filled=True)
        p.draw_circle(cx, cy, radius, 48, 49, 37, filled=True)
        p.draw_circle(cx, cy, radius-3, 62, 65, 45, filled=True)
        # 원본 스프라이트의 투명 여백까지 고정하여 별도 원화를 만들지 않는다.
        self.portrait.clip_draw(0, 384, 128, 128, cx, cy+3, radius*2.2, radius*2.2)

    def enemy_health(self, actor, x, y):
        self.begin()
        y += 44
        self.rounded(x-23, y-3, 46, 7, 3, (15, 17, 15, 240))
        fill = 42*max(0, actor.hp)/actor.max_hp
        if fill > 0:
            self.rounded(x-21, y-1, fill, 3, 1, (190, 106, 87, 255))
        self.rounded(x-23, y+7, 46, 16, 4, (25, 25, 22, 165))
        self.text(f'{actor.hp} / {actor.max_hp}', x, y+15, 11, (239, 229, 208))
        if actor.element == 'fire':
            self.rounded(x-38,y+25,76,16,4,(25,25,22,170))
            self.text('불 · 약점 물',x,y+33,10,(226,182,146))

    def hud(self, room, width, height):
        self.begin()
        cx = width/2
        top = height-22
        self.panel(24, top-64, 276, 64)
        self.portrait_badge(56, top-32)
        self.text('체력', 94, top-19, 12, self.muted, 'left')
        self.text(f'{room.player.hp} / {room.player.max_hp}', 278, top-19, 13, self.cream, 'right')
        bx, by, bw = 94, top-47, 184
        self.rounded(bx-1, by-1, bw+2, 13, 6, (12, 13, 11, 255))
        self.rounded(bx, by, bw, 11, 5, (63, 43, 37, 255))
        delta = max(0, min(.1, room.elapsed-self.last_time))
        if room.elapsed < self.last_time:
            self.hp_trail = room.player.hp
        self.last_time = room.elapsed
        self.hp_trail = max(room.player.hp, self.hp_trail-delta*50)
        self.rounded(bx, by, bw*self.hp_trail/room.player.max_hp, 11, 5, (153, 122, 76, 255))
        self.rounded(bx, by, bw*room.player.hp/room.player.max_hp, 11, 5, (174, 79, 65, 255))
        if room.player.hp > 0:
            self.p.draw_line(bx+5, by+8, bx+bw*room.player.hp/room.player.max_hp-4, by+8, 227, 143, 113, 100)
        self.panel(cx-108, top-58, 216, 58, accent=True)
        self.text(f'ROOM {room.stage:02d}', cx, top-13, 10, self.gold)
        self.text('첫 번째 방' if room.stage == 1 else '두 번째 방', cx, top-36, 20)
        for side in (-1, 1):
            self.p.draw_line(cx+side*120, top-29, cx+side*148, top-29, *self.gold, 100)
            self.diamond(cx+side*154, top-29, 2)
        self.panel(width-244, top-64, 220, 64)
        self.text('남은 적', width-134, top-16, 11, self.muted)
        for side in (-1, 1):
            self.diamond(width-134+side*60, top-39, 2)
        self.text(f'{room.remaining_enemies} / {len(room.enemies)}', width-134, top-39, 18)

        # 세 슬롯을 하나의 가운데 정렬 도크로 묶는다.
        dock_x, dock_y = cx-280, 12
        self.panel(dock_x, dock_y, 560, 66, radius=11)
        element_text = NAMES[room.selected]+(f' × {room.inventory[room.selected]}' if room.selected != 'neutral' else '')
        element_width = max(self.measure(element_text,16),self.measure('현재 원소',10))
        element_left = dock_x+84-(40+14+element_width)/2
        self.portrait_badge(element_left+20, 45, 18)
        element_text_x = element_left+54+element_width/2
        self.text(element_text,element_text_x,51,16)
        self.text('Q/E 원소 선택' if room.selected != 'neutral' else '현재 원소',element_text_x,31,10,self.muted)
        for x in (cx-112, cx+100):
            self.p.draw_line(x, 27, x, 63, *self.line, 120)
        self.key_label('SPACE','물 공격' if room.selected == 'water' else '기본 공격',cx,49,52)
        ready = 1-min(1, room.player.attack_cooldown/room.tuning.player_interval)
        self.rounded(cx-90, 25, 180, 4, 2, (63, 61, 47, 255))
        self.rounded(cx-90, 25, 180*ready, 4, 2, (184, 173, 118, 255))
        water = room.selected == 'water'
        skill_x = self.key_label('R','자가 회복' if water else '원소 없음',cx+190,49,28,13,
                                disabled=not water or room.player.hp >= room.player.max_hp)
        self.text('물 1개 소모' if water else '고유 스킬',skill_x,31,10,(107,108,95))
        self.key_label('ESC', '메뉴', width-66, 44, 36, 12)

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
            self.text(f'ROOM {stage:02d} COMPLETE' if outcome == 'clear' else 'TRY AGAIN',cx,cy+89,10,self.gold)
            self.text(('첫 번째 방 클리어' if stage == 1 else '두 번째 방 클리어') if outcome == 'clear' else '쓰러졌습니다',cx,cy+48,26)
            p.draw_line(cx-118, cy+12, cx+118, cy+12, *self.line)
            self.diamond(cx, cy+12, 3)
            self.rounded(cx-141, cy-66, 282, 44, 7, (106, 91, 58, 90))
            self.text('Enter  현재 방 다시 시작', cx, cy-44, 15)
            self.text('Esc  메뉴', cx, cy-99, 11, self.muted)

    def release(self):
        self.portrait = None
