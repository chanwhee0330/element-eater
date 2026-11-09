"""SDL 실제 렌더링: 방 전환, 1/2타 손상 루프 픽셀, 섭취/저장/물 전투."""
from pathlib import Path
from tempfile import TemporaryDirectory
import ctypes

from smoke_room_01 import p,ROOT,key,tick,capture
from src.application import Application


def frames(app,count):
    for _ in range(count):
        tick(app)
        app.draw()


def pixels(app,x,y,w,h):
    app.draw(present=False)
    buffer = (ctypes.c_uint8*(w*h*4))()
    rect = p.SDL_Rect(round(x),round(y),w,h)
    assert p.SDL_RenderReadPixels(p.pico2d.renderer,ctypes.byref(rect),p.SDL_PIXELFORMAT_RGBA32,buffer,w*4) == 0
    p.update_canvas()
    return bytes(buffer)


def tap(app,code):
    key(app,code)
    key(app,code,False)


def main():
    app = None
    with TemporaryDirectory() as temporary:
        save_path = Path(temporary)/'continue.json'
        p.open_canvas(Application.width,Application.height)
        try:
            p.hide_lattice()
            app = Application(p,save_path)
            key(app,p.SDLK_RETURN)
            assert app.room.stage == 1
            app.room.player.hp = 81
            for e in app.room.enemies:
                app.room.damage(e,e.max_hp)
            app.room.player.x,app.room.player.y = 10,3.6
            key(app,p.SDLK_w)
            for _ in range(30):
                tick(app)
            key(app,p.SDLK_w,False)
            assert app.room.stage == 2 and app.room.player.hp == 81
            assert app.room.player.y == 19.5
            capture(app,ROOT / 'outputs/previews/room-02/python-start.png')
            # 아래 무속성 교전이 끝난 상황에서 원천 동작을 분리해 검사한다.
            for e in app.room.enemies:
                if e.element == 'neutral':
                    app.room.damage(e,e.max_hp)
            app.room.projectiles.clear()
            app.room.player.x,app.room.player.y,app.room.player.facing = 5.5,14.5,'up'
            source = app.room.sources[0]
            root = (source.x,source.y)
            for damage_stage in (1,2):
                tap(app,p.SDLK_SPACE)
                frames(app,80)
                assert source.phase == f'damaged{damage_stage}'
                x,y = app.point(source.x,source.y)
                a = pixels(app,round(x-27),round(app.height-y-50),54,48)
                # 항아리 중앙의 고정 접점만 검사한다. 옆으로 새는 물방울은 움직여야 한다.
                base_a = pixels(app,round(x-3),round(app.height-y-7),6,5)
                frames(app,13)
                b = pixels(app,round(x-27),round(app.height-y-50),54,48)
                base_b = pixels(app,round(x-3),round(app.height-y-7),6,5)
                assert a != b, f'{damage_stage}타 뒤 실제 픽셀 애니메이션이 정지함'
                assert base_a == base_b, f'{damage_stage}타 뒤 고정 바닥 접점이 흔들림'
                assert (source.x,source.y) == root
                capture(app,ROOT / f'outputs/previews/room-02/water-damaged{damage_stage}.png')
            tap(app,p.SDLK_SPACE)
            frames(app,70)
            assert source.phase == 'orb'
            capture(app,ROOT / 'outputs/previews/room-02/water-orb.png')
            tap(app,p.SDLK_f)
            frames(app,24)
            assert source.phase == 'consumed' and app.room.inventory['water'] == 0
            app.save_progress()
            assert app.save_store.load()['stage'] == 2
            app.release()
            app = Application(p,save_path)
            app.continue_game()
            assert app.room.stage == 2
            frames(app,24)
            assert app.room.inventory['water'] == 1 and app.room.selected == 'water'
            # 같은 물 공격으로 두 번째 물 원천도 정확히 3회 파괴하고 누적 보관한다.
            app.room.player.x,app.room.player.y,app.room.player.facing = 14.5,14.5,'up'
            key(app,p.SDLK_SPACE)
            frames(app,145)
            key(app,p.SDLK_SPACE,False)
            frames(app,30)
            assert app.room.sources[1].phase == 'orb'
            tap(app,p.SDLK_f)
            frames(app,48)
            assert app.room.inventory['water'] == 2
            capture(app,ROOT / 'outputs/previews/room-02/python-water-form.png')
            tap(app,p.SDLK_r)
            frames(app,2)
            assert app.room.player.hp == 100 and app.room.inventory['water'] == 1
            tap(app,p.SDLK_r)
            frames(app,2)
            assert app.room.inventory['water'] == 1
            app.room.player.x,app.room.player.y,app.room.player.facing = 5.5,9.4,'up'
            fire = next(e for e in app.room.enemies if e.element == 'fire' and e.kind == 'melee')
            tap(app,p.SDLK_SPACE)
            frames(app,29)
            assert app.room.fire_aggro and fire.hp == 15
            assert app.room.inventory['water'] == 1 and fire.knockback_left == 0
            capture(app,ROOT / 'outputs/previews/room-02/python-water-combat.png')
            app.room.player.x,app.room.player.y = 14.5,8.8
            frames(app,40)
            assert any(s.owner == 'enemy' and s.element == 'fire' for s in app.room.projectiles)
            capture(app,ROOT / 'outputs/previews/room-02/python-fire-shot.png')
            app.return_to_title()
            assert app.continue_record['stage'] == 2
            app.continue_game()
            assert app.room.inventory['water'] == 1 and app.room.sources[0].phase == 'consumed'
            assert next(e for e in app.room.enemies if e.element == 'fire' and e.kind == 'melee').hp == 15
            app.restart()
            assert app.room.stage == 2 and app.room.player.hp == 100
            assert [s.phase for s in app.room.sources] == ['intact','intact']
            assert app.room.selected == 'neutral'
            print('PASS: stage 1->2, preserved HP, both damaged-loop pixel changes and fixed roots, break/orb, F ingestion, mid-ingest resume, inventory stack, healing consumption, water/fire combat, stage-2 save/restart')
        finally:
            if app:
                app.release()
            p.close_canvas()


if __name__ == '__main__':
    main()
