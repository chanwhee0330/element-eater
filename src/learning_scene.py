"""방 클리어 뒤 재생하는 원소 습득 연출."""
import math

from .elements import NAMES

LEARNING_ORDER = dict(enumerate(('water', 'fire', 'wind', 'earth', 'lightning'), 1))
LEARNING_SECONDS = 3.1
INGEST_START = .85
ORB_CONSUMED = INGEST_START + 4 / 12
TRANSFORM = INGEST_START + 8 / 12
COLORS = {
    'water': (112, 194, 255), 'fire': (255, 151, 75), 'wind': (175, 228, 118),
    'earth': (231, 168, 96), 'lightning': (223, 176, 255),
}


def draw_learning_scene(app, element, elapsed):
    p, ui = app.p, app.ui
    player = app.room.player
    x, foot = app.point(player.x, player.y)
    intro = app.water_intro
    seal_x, seal_y = (x + 35, foot + 38) if intro else app.seal_point()
    color = COLORS[element]
    transformed = elapsed >= TRANSFORM
    state = 'ingest' if INGEST_START <= elapsed < TRANSFORM else 'idle'
    form = element if transformed and not intro else app.room.selected
    key = ('hero', state) if form == 'neutral' else ('hero', state, form)
    meta = app.metadata[key]
    index = min(7, int((elapsed - INGEST_START) * 12)) if state == 'ingest' else 0
    frame = meta['frames'][f'down_{index}']
    clip, pivot = frame['pico2dClip'], frame['pivotPixelsTopLeft']
    width, height = clip['width'], clip['height']
    scale = app.unit / app.room.data['heroReferenceHeight']
    app.images[key].clip_draw(clip['left'], clip['bottom'], width, height,
                              x + (width / 2 - pivot['x']) * scale,
                              foot + (pivot['y'] - height / 2) * scale,
                              width * scale, height * scale)
    ui.begin()
    if elapsed < ORB_CONSUMED:
        progress = elapsed / ORB_CONSUMED
        approach = progress * progress * (3 - 2 * progress)
        orb_x = seal_x + (x - seal_x) * approach
        orb_y = seal_y + (foot + app.unit * .55 - seal_y) * approach
        size = (15 if intro else 35) * (1 - .55 * approach)
        app.source_images[element, 'orb'].draw(orb_x, orb_y, size, size)
    if ORB_CONSUMED <= elapsed < TRANSFORM + .5:
        progress = (elapsed - ORB_CONSUMED) / (TRANSFORM + .5 - ORB_CONSUMED)
        for i in range(12):
            angle = i * math.tau / 12
            distance = 9 + 55 * progress
            p.draw_circle(x + math.cos(angle) * distance,
                          foot + 26 + math.sin(angle) * distance * .66,
                          max(1, round(4 * (1 - progress))), *color, filled=True)
    if transformed and not intro:
        ui.panel(app.width / 2 - 168, 105, 336, 50, accent=True)
        ui.text(f'{NAMES[element]} 원소를 배웠다', app.width / 2, 130, 24, color)
