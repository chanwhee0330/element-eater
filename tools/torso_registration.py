"""몸색 상단과 손 위쪽 윤곽으로 몸통을 측정합니다. 귀·발끝은 제외합니다."""
from collections import deque
import numpy as np

BODY_MIN = {
    'neutral': (200, 170, 110), 'water': (110, 160, 170),
    'fire': (210, 130, 50), 'wind': (190, 190, 110),
    'earth': (210, 150, 95), 'lightning': (210, 170, 65),
}


def _run(line, center):
    center = int(round(center))
    if not line[center]:
        raise ValueError('몸통 측정 기준점이 투명합니다.')
    lo = hi = center
    while lo > 0 and line[lo - 1]: lo -= 1
    while hi + 1 < len(line) and line[hi + 1]: hi += 1
    return lo, hi


def fit_torso(image, element='neutral', expected=None):
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3] >= 128
    cx, cy, _, _ = expected or (64., 76., 34., 30.)
    light = alpha & np.all(pixels[:, :, :3] >= BODY_MIN[element], axis=2)
    light[:38] = False
    ys, xs = np.nonzero(light)
    index = np.argmin((xs-cx)**2 + (ys-(cy-17))**2)
    seed = (int(xs[index]), int(ys[index]))
    component = np.zeros_like(alpha)
    queue = deque([seed]); component[seed[1], seed[0]] = True
    while queue:
        x, y = queue.popleft()
        for xx, yy in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            if 0 <= xx < 128 and 0 <= yy < 128 and light[yy,xx] and not component[yy,xx]:
                component[yy,xx] = True; queue.append((xx,yy))
    for _ in range(2):
        columns = range(round(cx)-9, round(cx)+10)
        tops = [np.flatnonzero(component[:,x])[0] for x in columns if component[:,x].any()]
        assert len(tops) >= 10, ('몸통 색 영역 부족', element)
        top = float(np.percentile(tops, 25)) - 2
        bottom = float(np.percentile([_run(alpha[:,x],cy)[1] for x in columns],25))
        cy = (top+bottom)/2; ry = (bottom-top)/2+.5
        spans = []
        for y in range(round(cy-ry*.58),round(cy-ry*.28)+1):
            left,right = _run(alpha[y],cx)
            spans.append(((left+right)/2,(right-left)/2/np.sqrt(1-((y-cy)/ry)**2)))
        cx = float(np.median([s[0] for s in spans]))
        rx = float(np.percentile([s[1] for s in spans],35))
    return dict(cx=cx, cy=cy, rx=rx, ry=ry, support=len(tops)+len(spans),
                method='body-color-and-unoccluded-spans')
