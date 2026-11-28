"""북쪽 성문의 오원 봉인과 점등 연출."""

import math

from .boss import (COLORS, GATE_RUNE_TIMES, GATE_SEAL_SECONDS, GATE_SECONDS, GATE_SEQUENCE_SECONDS,
                   GATE_WATCH, RITUAL)
from .isometric import Mesh


RUNES = (
    (((0, 5), (-3, 1), (-3, -2), (0, -4), (3, -2), (3, 1), (0, 5)),),
    (((-2, -4), (-4, -1), (-2, 3), (-1, 1), (1, 5), (4, 0), (3, -3), (0, -4), (1, 0)),),
    (((-5, 1), (2, 1), (4, 2), (4, 4), (2, 5), (0, 4)), ((-4, -2), (2, -2), (3, -4), (1, -5))),
    (((-5, -3), (-1, 4), (2, 0), (3, 2), (5, -3), (-5, -3)), ((-1, 4), (-1, -3))),
    (((2, 5), (-3, 0), (1, 0), (-1, -5), (4, 1), (0, 1), (2, 5)),),
)
SOCKETS = ((-42, 45), (-33, 73), (0, 86), (33, 73), (42, 45))
GOLD = (255, 217, 150)
LIGHT = (255, 243, 205)
RUNE_BURST_SECONDS = .48


def light_quad(mesh, points, color, opacity):
    mesh.quad([(x, -y) for x, y in points], colors=[(*color, round(alpha)) for alpha in opacity])


def glow(mesh, x, y, rx, ry, color, opacity):
    edge = [(x + rx * math.cos(i * math.tau / 24), y + ry * math.sin(i * math.tau / 24))
            for i in range(25)]
    middle = [(x + (px - x) * .44, y + (py - y) * .44) for px, py in edge]
    for a, b, c, d in zip(edge, edge[1:], middle, middle[1:]):
        light_quad(mesh, (a, b, d, c), color, (0, 0, opacity * .44, opacity * .44))
        light_quad(mesh, (c, d, (x, y), (x, y)), color, (opacity * .44, opacity * .44, opacity, opacity))


def light_ray(mesh, start, end, width, color, opacity):
    x, y = start
    tx, ty = end
    length = math.hypot(tx - x, ty - y) or 1
    dx, dy = (ty - y) * width / length, (x - tx) * width / length
    for side in (-1, 1):
        edge = x + dx * side, y + dy * side
        outer = tx + dx * side * .42, ty + dy * side * .42
        light_quad(mesh, (start, edge, outer, end), color, (opacity, 0, 0, 0))


def arc(p, x, y, rx, ry, start, sweep, color, alpha, *, segments=16):
    for step in range(segments):
        a, b = start + sweep * step / segments, start + sweep * (step + 1) / segments
        p.draw_line(x + rx * math.cos(a), y + ry * math.sin(a),
                    x + rx * math.cos(b), y + ry * math.sin(b), *color, round(alpha))


def draw_glyph(p, index, x, y, scale, color, alpha):
    for stroke in RUNES[index]:
        for (ax, ay), (bx, by) in zip(stroke, stroke[1:]):
            p.draw_line(x + ax * scale, y + ay * scale, x + bx * scale, y + by * scale, *color, alpha)


def rune_stream(p, start, end, scale, color, progress):
    previous = None
    for index in range(12):
        t = progress - (11 - index) * .048
        if t < 0:
            continue
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t + scale * math.sin(math.pi * t) * 29
        if previous:
            for offset in (-4 * scale, -2 * scale, 0, 2 * scale, 4 * scale):
                p.draw_line(previous[0], previous[1] + offset, x, y + offset,
                            *color, 28 + index * (14 if abs(offset) <= 2 * scale else 6))
            p.draw_line(*previous, x, y, *LIGHT, 35 + index * 19)
        previous = x, y
    if previous:
        p.draw_circle(*previous, round(3.5 * scale), *color, 245, filled=True)


def rune_burst(app, element, index, x, y, scale, color, age):
    ui, p = app.ui, app.p
    progress = age / RUNE_BURST_SECONDS
    fade = (1 - progress) ** 1.35
    radius = scale * (13 + progress * 38)
    mesh = Mesh()
    glow(mesh, x, y, radius * 1.42, radius * 1.32, color, 161 * fade)
    mesh.draw(p, offset=(0, app.height - 1))
    if element in ('water', 'wind'):
        for ring in range(3):
            size = radius * (1 + ring * .22)
            sweep = math.tau * .74 if element == 'water' else math.pi * 1.1
            arc(p, x, y, size, size * (.53 if element == 'water' else .83),
                progress * (2 + ring) + ring * 2.1, sweep, color, (205 - ring * 36) * fade)
    if element == 'lightning' and progress < .51:
        for branch in range(5):
            angle = branch * math.tau / 5 + progress
            px, py = x + math.cos(angle) * radius * 1.6, y + math.sin(angle) * radius * 1.6
            app.draw_electric_arc(x, y, px, py, 8 * scale, round(218 * fade), branch,
                                  glow=color, core=(248, 223, 255))
    for i in range(18):
        angle = i * 2.399 + index
        distance = scale * (9 + (31 + i % 5 * 9) * progress)
        px = x + math.cos(angle) * distance
        py = y + math.sin(angle) * distance
        if element == 'fire':
            py += scale * 40 * progress
        elif element == 'earth':
            py -= scale * 37 * progress**2
        p.draw_line(x + (px - x) * .79, y + (py - y) * .79, px, py, *color, round(206 * fade))
        size = 1 + i % 3 + (2 if element == 'earth' else 0)
        ui.diamond(px, py, scale * size * fade, (*(LIGHT if i % 3 else color), round(242 * fade)))
    if progress < .70:
        draw_glyph(p, index, x, y + progress * 19 * scale, scale * (1.5 + 3.5 * progress),
                   LIGHT, round(225 * fade))


def draw_gate_seal(app, x, y, scale):
    g, ui = app.room.guardian, app.ui
    p = ui.p
    age = g.gate_elapsed
    core = x, y + 29 * scale
    ui.begin()
    if GATE_RUNE_TIMES[-1] <= age < GATE_SEAL_SECONDS:
        gather_light(app, *core, scale, age)
    for index, (offset_x, offset_y) in enumerate(SOCKETS):
        px, py = x + offset_x * scale, y + offset_y * scale
        element = RITUAL[index]
        tone = COLORS[element]
        since = age - GATE_RUNE_TIMES[index]
        lit = index < g.gate_runes
        alpha = 255 if lit else 175
        if 0 <= age < GATE_RUNE_TIMES[index] and since > -.29:
            rune_stream(p, core, (px, py), scale, tone, 1 + since / .29)
        if lit and since < RUNE_BURST_SECONDS:
            rune_burst(app, element, index, px, py, scale, tone, since)
        if lit:
            ui.orb_socket_glow(px, py, round(7 * scale), tone)
        ui.diamond(px, py, 10 * scale, (*(tone if lit else (155, 121, 95)), alpha))
        ui.diamond(px, py, 8 * scale, (44, 33, 53, 255))
        draw_glyph(p, index, px, py, scale, tone if lit else (201, 164, 125), alpha)
        if GATE_RUNE_TIMES[-1] <= age < GATE_SEAL_SECONDS:
            progress = (age - GATE_RUNE_TIMES[-1]) / (GATE_SEAL_SECONDS - GATE_RUNE_TIMES[-1])
            rune_stream(p, (px, py), core, scale, tone, progress)

    openness = g.gate_progress
    if openness < 1:
        pulse_time = age if age >= 0 else app.room.elapsed
        pulse = .6 + .4 * math.sin(pulse_time * 5) ** 2 if g.reward_tasted else .3
        alpha = round((1 - openness) * (160 + 95 * pulse))
        ui.diamond(*core, 15 * scale, (*GOLD, alpha))
        ui.diamond(*core, 12 * scale, (42, 29, 45, alpha))
        ui.diamond(*core, 5 * scale, (*LIGHT, alpha))
    if GATE_SEAL_SECONDS <= age < GATE_SEQUENCE_SECONDS:
        draw_opening_light(app, x, y, scale, age - GATE_SEAL_SECONDS, openness)
    elif 0 <= age < .40:
        impact = 1 - age / .40
        mesh = Mesh()
        glow(mesh, *core, scale * (46 + 100 * age), scale * (51 + 120 * age), GOLD, 184 * impact)
        mesh.draw(p, offset=(0, app.height - 1))
        arc(p, *core, scale * (18 + 115 * age), scale * (18 + 115 * age), 0, math.tau,
            GOLD, 210 * impact, segments=30)


def gather_light(app, x, y, scale, age):
    charge = (age - GATE_RUNE_TIMES[-1]) / (GATE_SEAL_SECONDS - GATE_RUNE_TIMES[-1])
    p, ui = app.p, app.ui
    radius = scale * (66 - 26 * charge)
    mesh = Mesh()
    glow(mesh, x, y, radius * 1.66, radius * 1.4, GOLD, 125 * charge)
    mesh.draw(p, offset=(0, app.height - 1))
    for index, element in enumerate(RITUAL):
        angle = index * math.tau / len(RITUAL) + charge * 1.65
        arc(p, x, y, radius, radius * .78, angle, .88, COLORS[element], 130 + 115 * charge)
        px, py = x + radius * math.cos(angle), y + radius * .78 * math.sin(angle)
        ui.diamond(px, py, scale * 3, (*LIGHT, round(210 * charge)))


def draw_opening_light(app, x, foot, scale, age, openness):
    p, ui = app.p, app.ui
    y = foot + 29 * scale
    flash = max(0, 1 - age / .69) ** 1.37
    afterglow = max(0, 1 - (age - GATE_SECONDS) / GATE_WATCH)
    strength = min(openness * 2, 1) * min(1, afterglow)
    mesh = Mesh()
    if strength:
        for left, right in ((-1, -.70), (-.70, .70), (.70, 1)):
            light_quad(mesh, ((x+25*left*scale, foot), (x+25*right*scale, foot),
                              (x+87*right*scale, foot-184*scale), (x+87*left*scale, foot-184*scale)),
                       GOLD, (179*strength*(abs(left) < 1), 179*strength*(abs(right) < 1), 0, 0))
        light_quad(mesh, ((x-25*scale, foot), (x+25*scale, foot),
                          (x+23*scale, foot+42*openness*scale), (x-23*scale, foot+42*openness*scale)),
                   LIGHT, (145*strength, 145*strength, 115*strength, 115*strength))
        glow(mesh, x, foot - 4 * scale, 76 * scale, 48 * scale, GOLD, 111 * strength)
    if flash:
        glow(mesh, x, y, (118 + age * 95) * scale, (106 + age * 68) * scale, GOLD, 158 * flash)
        glow(mesh, x, y, 48 * scale, 43 * scale, LIGHT, 204 * flash)
        for index, element in enumerate(RITUAL):
            angle = math.tau * index / len(RITUAL) + .3 + age
            reach = scale * (167 + 155 * age)
            end = x + math.cos(angle) * reach, y + math.sin(angle) * reach * .76
            color = COLORS[element]
            light_ray(mesh, (x, y), end, 28 * scale, color, 213 * flash)
            light_ray(mesh, (x, y), end, 5 * scale, LIGHT, 248 * flash)
    mesh.draw(p, offset=(0, app.height - 1))
    if flash:
        for index in range(3):
            radius = scale * (24 + index * 17 + age * 169)
            arc(p, x, y, radius, radius * .92, 0, math.tau, GOLD, (239 - index * 38) * flash, segments=48)
        ui.diamond(x, y, scale * (13 + 17 * flash), (*LIGHT, round(216 * flash)))
    if age < .93:
        wave = age / .93
        radius = (21 + 169 * wave) * scale
        for i, element in enumerate(RITUAL):
            angle = i * math.tau / len(RITUAL) + .46
            arc(p, x, foot - wave * 51 * scale, radius, radius * .45, angle, 1.14,
                COLORS[element], 222 * (1 - wave), segments=19)
        for i in range(43):
            angle = i * 2.399
            distance = (25 + (66 + i % 11 * 15) * wave) * scale
            px, py = x + math.cos(angle) * distance, y + math.sin(angle) * distance * .72
            color = COLORS[RITUAL[i % len(RITUAL)]] if i % 4 else LIGHT
            ui.diamond(px, py, scale * (2 + i % 4) * (1 - wave), (*color, round(240 * (1 - wave))))
    for index in range(45 if strength else 0):
        phase = (age * (.8 + index % 7 * .14) + index * .13) % 1
        px = x + scale * ((index * 31 % 123 - 61) * (.37 + phase))
        py = y + scale * (phase * 159 - 44)
        color = COLORS[RITUAL[index % len(RITUAL)]] if index % 3 else GOLD
        ui.diamond(px, py, scale * (1 + index % 3), (*color, round(236 * (1 - phase) * strength)))
