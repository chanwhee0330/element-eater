"""기존 주인공 스프라이트의 앞과 뒤를 도는 오원 아우라."""
import math

from .boss import COLORS, RITUAL


def draw_master_aura(app, x, foot, size, elapsed, *, front):
    ui, p = app.ui, app.p
    ui.begin()
    for index, element in enumerate(RITUAL):
        angle = elapsed*1.85 + index*math.tau/len(RITUAL)
        depth = math.sin(angle)
        if (depth < 0) != front:
            continue
        px = x + size*.69*math.cos(angle)
        py = foot + size*(.36 + .27*depth)
        color = COLORS[element]
        step = size / 54
        # 작은 흔적을 남겨 다섯 효과가 몸 주위를 흐르는 방향을 보여 준다.
        for trail in range(1, 6):
            past = angle - trail*.14
            ui.diamond(x + size*.69*math.cos(past), foot + size*(.36+.27*math.sin(past)),
                       max(1, (4-trail)*step), (*color, 155-trail*24))
        if element == 'water':
            ui.diamond(px, py+3*step, 4*step, (65, 167, 224))
            p.draw_circle(px, py-step, max(1, round(4*step)), *color, 240, filled=True)
            ui.diamond(px-step, py+step, 1.5*step, (222, 251, 255))
        elif element == 'fire':
            flicker = math.sin(elapsed*19)*step
            ui.diamond(px, py, 5*step, (238, 101, 53))
            ui.diamond(px+step, py+4*step+flicker, 3*step, (245, 126, 66))
            p.draw_line(px+step, py+4*step, px-step, py+8*step+flicker, 255, 159, 68)
            ui.diamond(px, py-step, 3*step, (255, 210, 115))
        elif element == 'wind':
            for lift, span in ((0, 7), (3, 5), (-3, 4)):
                points = ((-span, lift+1), (-2, lift-1), (2, lift-1), (span, lift+1))
                for a, b in zip(points, points[1:]):
                    p.draw_line(px+a[0]*step, py+a[1]*step, px+b[0]*step, py+b[1]*step, *color, 230)
            ui.diamond(px+4*step, py+2*step, 2*step, (205, 247, 164))
        elif element == 'earth':
            for shift_x, shift_y, radius in ((-3, -2, 3), (3, 1, 4)):
                ui.diamond(px+shift_x*step, py+shift_y*step, radius*step, (166, 115, 76))
                ui.diamond(px+shift_x*step, py+(shift_y+1)*step, (radius-1)*step, (*color, 240))
            ui.diamond(px+2*step, py+2*step, step, (255, 231, 175))
        else:
            points = ((px+3*step, py+6*step), (px-step, py+step),
                      (px+2*step, py), (px-3*step, py-5*step))
            for a, b in zip(points, points[1:]):
                p.draw_line(*a, *b, *color, 245)
                p.draw_line(a[0]+1, a[1], b[0]+1, b[1], 245, 214, 255, 230)
