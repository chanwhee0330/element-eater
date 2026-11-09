"""타이틀의 실제 SDL 마우스/키 입력과 저장 후 재실행 이어하기 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import ctypes

from smoke_room_01 import p, ROOT, key, tick, capture
from src.application import Application
from src.title import buttons


def click(app, index):
    x, y, w, h = buttons(app.width)[index]
    event = p.SDL_Event()
    event.type = p.SDL_MOUSEBUTTONDOWN
    event.button.button = p.SDL_BUTTON_LEFT
    event.button.x = round(x+w/2)
    event.button.y = round(app.height-y-h/2)
    assert p.SDL_PushEvent(ctypes.byref(event)) == 1
    app.handle(p.get_events())


def main():
    app = None
    with TemporaryDirectory() as temporary:
        save_path = Path(temporary) / 'continue.json'
        p.open_canvas(Application.width, Application.height)
        try:
            p.hide_lattice()
            app = Application(p, save_path)
            assert app.scene == 'title' and app.continue_record is None
            capture(app, ROOT / 'outputs/previews/title-screen/title-no-save.png')
            click(app, 0)
            assert app.scene == 'title' and not save_path.exists()
            key(app, p.SDLK_LEFT)
            assert app.title_index == 2  # 비활성 이어하기를 건너뛴다.
            key(app, p.SDLK_RIGHT)
            assert app.title_index == 1
            click(app, 1)
            assert app.scene == 'play' and app.room.player.hp == 100
            assert save_path.exists()
            key(app, p.SDLK_w)
            for _ in range(60):
                tick(app)
            key(app, p.SDLK_w, False)
            app.room.damage(app.room.player, 15)
            app.room.damage(app.room.enemies[0], 5)
            saved_position = app.room.player.x, app.room.player.y
            # Esc의 타이틀 돌아가기로 저장한 뒤 실제 객체도 새로 만든다.
            key(app, p.SDLK_ESCAPE)
            key(app, p.SDLK_DOWN)
            key(app, p.SDLK_DOWN)
            key(app, p.SDLK_RETURN)
            assert app.scene == 'title' and app.continue_record['stage'] == 1
            app.release()
            app = Application(p, save_path)
            assert app.scene == 'title' and app.continue_record['stage'] == 1
            app.title_index = 0
            capture(app, ROOT / 'outputs/previews/title-screen/title-with-save.png')
            click(app, 0)
            assert app.scene == 'play' and app.room.player.hp == 85
            assert (app.room.player.x, app.room.player.y) == saved_position
            assert app.room.enemies[0].hp == 25
            app.return_to_title()
            click(app, 1)
            assert app.room.player.hp == 100 and app.room.remaining_enemies == 4
            assert app.room.player.y == 19.5
            # 실제 자동 저장 간격이 지나면 파일에도 변경 상태가 반영된다.
            app.room.player.hp = 80
            for _ in range(125):
                tick(app)
            assert app.save_store.load()['state']['player']['hp'] == 80
            app.room.outcome = 'clear'
            tick(app)
            assert app.room.stage == 2 and app.save_store.load()['stage'] == 2
            app.return_to_title()
            assert app.continue_record['stage'] == 2
            app.title_index = 0
            capture(app,ROOT / 'outputs/previews/title-screen/title-stage-02.png')
            click(app,0)
            assert app.room.stage == 2
            app.room.outcome = 'clear'
            tick(app)
            assert app.save_store.load() is None
            app.return_to_title()
            assert app.continue_record is None
            click(app, 0)
            assert app.scene == 'title'
            click(app, 2)
            assert not app.running
            print('PASS: title mouse/keyboard, disabled continue, stage caption, new game, autosave, return to title, reload/resume, clear, exit')
        finally:
            if app:
                app.release()
            p.close_canvas()


if __name__ == '__main__':
    main()
