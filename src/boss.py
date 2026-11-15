"""원소 변환 보스의 공격 예고와 실행."""
import math

from .combat import Projectile
from .elements import WEAKNESS

FORMS = ('fire', 'wind', 'earth', 'lightning', 'water')
FORM_SECONDS = 8
WARNING_SECONDS = 1


def update_boss(room, dt):
    boss = room.enemies[0]
    if not boss.active:
        room.boss_warning = None
        room.projectiles[:] = [shot for shot in room.projectiles if shot.owner == 'hero']
        return
    previous = int(room.boss_time / FORM_SECONDS)
    room.boss_time += dt
    phase = int(room.boss_time / FORM_SECONDS)
    boss.animation_time += dt
    boss.hit_flash = max(0, boss.hit_flash - dt)
    if phase != previous:
        boss.element = FORMS[phase % len(FORMS)]
        room.boss_burn_until = 0
        boss.knockback_left = 0
        room.boss_warning = None
        room.projectiles[:] = [shot for shot in room.projectiles if shot.owner == 'hero']
        weakness = WEAKNESS[boss.element]
        sources = [source for source in room.sources if source.element == weakness]
        if sources and not room.inventory[weakness] and all(source.phase == 'consumed' for source in sources):
            min(sources, key=lambda source: math.hypot(room.player.x-source.x,
                                                       room.player.y-source.y)).age = 3
    if room.boss_burn_tick <= room.boss_time <= room.boss_burn_until and room.boss_burn_until:
        room.boss_burn_tick += .5
        room.damage(boss, 3)
        if not boss.active:
            room.boss_warning = None
            room.projectiles[:] = [shot for shot in room.projectiles if shot.owner == 'hero']
            return
    if boss.knockback_left > 0:
        step = min(dt, boss.knockback_left)
        dx, dy = boss.knockback
        move_boss(room, boss, dx * step, dy * step)
        boss.knockback_left -= step
    if room.boss_time % FORM_SECONDS < 1:
        return
    if room.boss_warning:
        if room.boss_time >= room.boss_warning[2]:
            x, y, _ = room.boss_warning
            room.boss_warning = None
            room.boss_next_attack = room.boss_time + 1.15
            attack(room, boss, x, y)
    elif not room.player.falling and room.boss_time >= room.boss_next_attack and room.boss_time % FORM_SECONDS < 7:
        room.boss_warning = (room.player.x, room.player.y, room.boss_time + WARNING_SECONDS)


def move_boss(room, boss, dx, dy):
    left, top, right, bottom = room.boss['arena']
    x = min(right, max(left, boss.x + dx))
    y = min(bottom, max(top, boss.y + dy))
    room.move(boss, x - boss.x, y - boss.y, safe=True)


def attack(room, boss, x, y):
    player = room.player
    if boss.element == 'earth':
        if math.hypot(player.x - x, player.y - y) < 1.15:
            room.damage(player, 10)
        return
    dx, dy = x - boss.x, y - boss.y
    angle = math.atan2(dy, dx)
    if boss.element == 'wind':
        old_x, old_y = boss.x, boss.y
        move_boss(room, boss, math.cos(angle) * 6, math.sin(angle) * 6)
        vx, vy = boss.x - old_x, boss.y - old_y
        length2 = vx * vx + vy * vy
        along = ((player.x - old_x) * vx + (player.y - old_y) * vy) / (length2 or 1)
        along = min(1, max(0, along))
        if math.hypot(player.x - old_x - along * vx, player.y - old_y - along * vy) < .8:
            room.damage(player, 10)
        return
    offsets, speed = {
        'fire': ((-.55, -.28, 0, .28, .55), 9),
        'lightning': ((0,), 15),
        'water': ((-.95, -.62, -.3, 0, .3, .62, .95), 5),
    }[boss.element]
    for offset in offsets:
        heading = angle + offset
        room.projectiles.append(Projectile(boss.x, boss.y, math.cos(heading), math.sin(heading),
                                           'enemy', 10, speed, 24, element=boss.element))
