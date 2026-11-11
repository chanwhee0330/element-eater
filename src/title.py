"""타이틀 버튼 배치와 렌더링. 좌표는 pico2d 왼쪽 아래 원점."""
LABELS = ('이어하기', '새게임 시작', '종료')


def buttons(width):
    return [(width/2+offset-106, 42, 212, 52) for offset in (-250, 0, 250)]


def hit_test(x, y, width):
    for i, (left, bottom, w, h) in enumerate(buttons(width)):
        if left <= x < left+w and bottom <= y < bottom+h:
            return i
    return None


def draw_title(app):
    p, ui = app.p, app.ui
    app.title_image.draw(app.width/2, app.height/2, app.width, app.height)
    ui.begin()
    for i, (x, y, w, h) in enumerate(buttons(app.width)):
        enabled = i != 0 or app.continue_record is not None
        selected = i == app.title_index and enabled
        ui.panel(x, y, w, h, accent=selected)
        if selected:
            ui.rounded(x+3, y+3, w-6, h-6, 7, (134, 109, 57, 70))
            ui.diamond(x+19, y+h/2, 3)
            ui.diamond(x+w-19, y+h/2, 3)
        ui.text(LABELS[i], x+w/2, y+h/2+1, 18,
                ui.cream if enabled else (107, 102, 91))
        if i == 0:
            subtitle = f'{app.continue_record["stage"]}번 스테이지' if enabled else '저장된 게임 없음'
            ui.text(subtitle, x+w/2, y-17, 11, ui.gold if enabled else (112, 105, 92))
    ui.text('1 · 2 · 3  스테이지 바로가기', app.width / 2, 122, 13, ui.cream)
    if app.save_error:
        ui.text(app.save_error, app.width/2, 148, 12, (226, 162, 127))
