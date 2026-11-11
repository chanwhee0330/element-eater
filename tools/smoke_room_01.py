"""실제 pico2d/SDL 창에서 키 입력·렌더링·일시정지·재시작·종료 검증.

실행: .venv/Scripts/python.exe tools/smoke_room_01.py
"""
from pathlib import Path
import ctypes
import os
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pico2d as p
from src.application import Application


def key(app, code, down=True):
    event = p.SDL_Event()
    event.type = p.SDL_KEYDOWN if down else p.SDL_KEYUP
    event.key.keysym.sym = code
    event.key.repeat = 0
    assert p.SDL_PushEvent(ctypes.byref(event)) == 1
    app.handle(p.get_events())


def tick(app):
    # SDL 큐에 직접 보낸 입력 검사는 OS의 전경 창 전환 제한과 독립적으로 실행한다.
    # 실제 실행에서는 focused 기본값으로 네이티브 창 플래그를 읽는다.
    app.step(1/60, focused=True)


def capture(app, path):
    app.draw(present=False)
    surface = p.SDL_CreateRGBSurfaceWithFormat(0, app.width, app.height, 32, p.SDL_PIXELFORMAT_RGBA32)
    try:
        assert surface
        assert p.SDL_RenderReadPixels(p.pico2d.renderer, None, surface.contents.format.contents.format,
                                      surface.contents.pixels, surface.contents.pitch) == 0
        path.parent.mkdir(parents=True, exist_ok=True)
        assert p.IMG_SavePNG(surface, str(path).encode('utf-8')) == 0
    finally:
        p.SDL_FreeSurface(surface)
    p.update_canvas()


def main():
    app = None
    temporary = TemporaryDirectory()
    p.open_canvas(Application.width, Application.height)
    try:
        p.hide_lattice()
        app = Application(p, Path(temporary.name) / 'continue.json')
        app.new_game()
        p.SDL_RaiseWindow(p.pico2d.window)
        p.delay(.15)
        p.SDL_PumpEvents()
        capture(app, ROOT / 'outputs/previews/room-01/python-start.png')
        initial = [(e.x, e.y) for e in app.room.enemies]
        key(app, p.SDLK_w)
        for i in range(160):
            tick(app)
            if i % 15 == 0:
                app.draw()
            if i == 130:
                assert not app.room.aggro
                assert initial == [(e.x, e.y) for e in app.room.enemies]
        key(app, p.SDLK_w, False)
        assert app.room.aggro
        for i in range(120):
            tick(app)
            if i % 15 == 0:
                app.draw()
        assert all(e.x != initial[i][0] for i, e in enumerate(app.room.enemies[:2]))
        assert [(e.x, e.y) for e in app.room.enemies[2:]] == initial[2:]
        capture(app, ROOT / 'outputs/previews/room-01/python-chase.png')
        # 짧게 눌렀다 뗀 Space도 한 번 발동하고 실제 적 체력이 줄어든다.
        key(app, p.SDLK_a)
        tick(app)
        key(app, p.SDLK_a, False)
        key(app, p.SDLK_SPACE)
        key(app, p.SDLK_SPACE, False)
        for _ in range(65):
            tick(app)
        assert any(e.hp < e.max_hp for e in app.room.enemies), '실제 Space 입력으로 적 피격'
        # 위 왼쪽으로 이동해 원거리의 예고·탄환과 플레이어 탄환을 함께 렌더링한다.
        key(app, p.SDLK_a)
        for _ in range(76):
            tick(app)
        key(app, p.SDLK_a, False)
        key(app, p.SDLK_w)
        for _ in range(48):
            tick(app)
        key(app, p.SDLK_w, False)
        key(app, p.SDLK_SPACE)
        for _ in range(29):
            tick(app)
        capture(app, ROOT / 'outputs/previews/room-01/python-combat.png')
        assert app.room.projectiles, '탄환 렌더링 시나리오'
        key(app, p.SDLK_SPACE, False)
        key(app, p.SDLK_ESCAPE)
        before = app.room.elapsed
        bullets = [(s.x, s.y, s.age) for s in app.room.projectiles]
        key(app, p.SDLK_w)
        for _ in range(60):
            tick(app)
        assert app.paused and app.room.elapsed == before
        assert bullets == [(s.x, s.y, s.age) for s in app.room.projectiles]
        capture(app, ROOT / 'outputs/previews/room-01/python-pause.png')
        key(app, p.SDLK_ESCAPE)
        assert not app.paused and not app.keys
        key(app, p.SDLK_ESCAPE)
        key(app, p.SDLK_DOWN)
        key(app, p.SDLK_RETURN)
        assert not app.room.aggro and app.room.player.y == 19.5
        assert not app.room.projectiles and app.room.player.hp == app.room.player.max_hp
        assert all(e.hp == e.max_hp for e in app.room.enemies)
        # 승패 화면에서도 Enter 입력으로 현재 방을 재시작한다.
        app.room.damage(app.room.player, app.room.player.max_hp)
        assert app.room.outcome == 'dead'
        app.draw()
        key(app, p.SDLK_RETURN)
        assert app.room.outcome is None and app.room.player.hp == 100
        for enemy in app.room.enemies:
            app.room.damage(enemy, enemy.max_hp)
        app.room.player.x = app.room.data['plannedExit']['x']
        app.room.player.y = app.room.data['plannedExit']['y']
        tick(app)
        assert app.room.stage == 2 and app.room.outcome is None
        assert app.save_store.load()['stage'] == 2
        # 다음 검사는 2→3번 전환과 마지막 방 클리어/재시작도 확인한다.
        for enemy in app.room.enemies:
            app.room.damage(enemy,enemy.max_hp)
        app.room.player.x = app.room.data['plannedExit']['x']
        app.room.player.y = app.room.data['plannedExit']['y']
        tick(app)
        assert app.room.stage == 3 and app.room.outcome is None
        assert app.save_store.load()['stage'] == 3
        # 3번 방의 마지막 출구는 소각과 적 처치 후 클리어한다.
        app.room.vine_time = app.room.vine_gate['burnDuration']
        for enemy in app.room.enemies:
            app.room.damage(enemy, enemy.max_hp)
        exit_point = app.room.data['plannedExit']
        app.room.player.x, app.room.player.y = exit_point['x'], exit_point['y']
        tick(app)
        assert app.room.outcome == 'clear'
        capture(app, ROOT / 'outputs/previews/room-03/python-clear.png')
        key(app, p.SDLK_RETURN)
        assert app.room.remaining_enemies == 4 and not app.room.outcome
        app.new_game()
        # 회귀: 원거리 적을 넉백시키면 walk 렌더링이 필요하다. 매 프레임 그려야 잡힌다.
        ranged = app.room.enemies[2]
        for enemy in app.room.enemies:
            enemy.active = enemy is ranged
        app.room.player.x, app.room.player.y, app.room.player.facing = 8, 19, 'right'
        ranged.x, ranged.y = 10, 19
        key(app, p.SDLK_SPACE)
        key(app, p.SDLK_SPACE, False)
        rendered_knockback = False
        for _ in range(50):
            tick(app)
            app.draw()
            rendered_knockback |= ranged.moving and ranged.attack_elapsed < 0
        assert ranged.hp == ranged.max_hp-15 and rendered_knockback
        app.restart()
        key(app, p.SDLK_r)
        assert not app.paused and app.room.player.y == 19.5
        key(app, p.SDLK_w)
        p.SDL_HideWindow(p.pico2d.window)
        p.SDL_PumpEvents()
        app.step(1/60)
        assert app.paused and not app.keys, '포커스 상실 시 입력 해제·자동 정지'
        p.SDL_ShowWindow(p.pico2d.window)
        quit_event = p.SDL_Event()
        quit_event.type = p.SDL_QUIT
        p.SDL_PushEvent(ctypes.byref(quit_event))
        app.handle(p.get_events())
        assert not app.running
        print('PASS: SDL 이동/Space 입력, 진입 추격, 탄환/적 피격/체력, HUD 렌더링, 전투 일시정지, 재시작 초기화, 포커스 상실, 정상 종료')
    finally:
        if app:
            app.release()
        p.close_canvas()
        temporary.cleanup()


if __name__ == '__main__':
    main()
