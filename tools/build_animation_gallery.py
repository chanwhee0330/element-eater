"""기존 애니메이션을 모은 이미지 내장형 HTML 목록을 생성합니다."""
from pathlib import Path
from html import escape
import base64
import io

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/previews"


def embedded(path, width=660):
    """원본을 보존하고 목록용 이미지만 메모리에서 축소합니다."""
    path = OUT / path
    with Image.open(path) as source:
        if source.format != "GIF":
            image = source.convert("RGB")
            image.thumbnail((width, width), Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            image.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            frames, durations = [], []
            for i in range(source.n_frames):
                source.seek(i)
                image = source.convert("RGB")
                image.thumbnail((width, width), Image.Resampling.LANCZOS)
                frames.append(image.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
                durations.append(source.info.get("duration", 100))
            buf = io.BytesIO()
            frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                           duration=durations, loop=0, disposal=2, optimize=True)
            mime = "image/gif"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


CARDS = [
    dict(id="enemies", tag="무속성·원소 적 · 근접형 / 원거리형", title="무속성 + 5원소 × 두 유형 × 세 동작",
         image="elemental-enemies/melee.gif", page="elemental-enemies/preview.html",
         text="두 눈과 큰 주먹의 근접형, 외눈과 발사구의 원거리형. 원소 장식 없는 회색 무속성 포함 12종·36시트·4방향·1,152프레임이며 몸통 크기와 중심을 고정합니다.",
         hint="상세 재생기에서 두 유형·세 동작을 비교하거나 전체 12종을 보고, 한 프레임씩 몸통 기준선을 확인합니다. 이미지 시안이며 본게임 AI·전투는 미연결입니다.",
         scripts=[("tools/build_elemental_enemies.py", "고정 몸통·관절 부품 애니메이션 조립과 픽셀 검사"),
                  ("tools/elemental_enemies_preview.html", "원소·방향·동작·프레임 비교 재생기")]),
    dict(id="projectiles", tag="기본 공격 · 원소별 투사체", title="무속성 + 5원소 비행 애니메이션",
         image="basic-projectiles/projectiles.gif", page="basic-projectiles/preview.html",
         text="아이보리 충격탄·물방울탄·불꽃탄·회오리탄·돌조각탄·전기탄. 6종 모두 4방향 × 8프레임의 투명 PNG/JSON 시트로 준비했습니다.",
         hint="상세 재생기에서 캐릭터 발사와 확대 비행 루프를 확인합니다. Space 기본 공격용 시안이며 R 고유 스킬과 본게임 전투 판정은 별도입니다.",
         scripts=[("tools/build_basic_projectiles.py", "원화 등록·방향별 시트·GIF 생성"),
                  ("tools/basic_projectiles_preview.html", "캐릭터 발사·비행 재생기")]),
    dict(id="hero", tag="캐릭터 · 최신 중심 정렬", title="6가지 모습 × 4가지 동작",
         image="hero-elements/preview-fallback.gif", page="hero-elements/preview.html",
         text="무속성·물·불·바람·흙·번개의 대기, 걷기, Space 기본 공격, F 구슬 먹기. 각 동작은 4방향 × 8프레임이며 전체 24개 시트·768프레임입니다.",
         hint="상세 재생기에서 원소·방향 선택, 일시정지, 다시 재생을 할 수 있습니다.",
         scripts=[("tools/build_hero_registered.py", "최종 시트 생성·몸통 중심 정렬"),
                  ("tools/hero_elements_preview.html", "캐릭터 재생 스크립트"),
                  ("tools/standalone_hero_preview.py", "이미지·움직이는 대체 화면 내장")]),
    dict(id="idle", tag="원소 오브젝트 · 대기", title="맵 위의 원소 오브젝트 5종",
         image="element-pickups/element-pickups-refined-animation.gif",
         page="element-pickups/element-pickups-preview.html",
         text="물 항아리의 잔물결, 장작의 불꽃, 바람개비 회전, 작은 돌의 움직임, 전지의 전기 점멸을 반복합니다. 바람은 24프레임, 나머지는 8프레임입니다.",
         hint="상세 재생기에서 맵 배치와 확대 동작, 재생 속도를 확인합니다.",
         scripts=[("tools/build_element_pickups.py", "대기 시트 생성"),
                  ("tools/bake_pickup_layers.py", "고정 본체·움직이는 효과 합성"),
                  ("tools/element_pickups_preview.js", "대기 애니메이션 재생")]),
    dict(id="damage", tag="원소 오브젝트 · 최신 v3", title="손상 1·2단계도 계속 움직이기",
         image="element-destruction-v3/damaged-idle-loops.gif",
         page="element-destruction-v3/preview.html",
         text="다섯 오브젝트 각각의 손상 1단계·2단계 전용 반복 동작, 총 10개 루프입니다. 다음 공격 전까지 손상과 움직임을 유지하고 타격 흔들림 뒤 원래 위치로 돌아옵니다.",
         hint="상세 재생기에서 한 번, 두 번 공격한 뒤 기다려 보면 손상 동작이 유지됩니다.",
         scripts=[("assets/items/elements/break-release-v3/state-machine.mjs", "내구도·파괴·구슬 상태 전이"),
                  ("outputs/previews/element-destruction-v3/preview.html", "손상 루프·공격·흔들림 재생")]),
    dict(id="release", tag="원소 오브젝트 · 파괴 / 방출", title="3타 또는 약점 1타 → 원소 구슬",
         image="element-destruction-v2/comparison.gif",
         page="element-destruction-v3/preview.html",
         text="약점이 아닌 공격은 3회, 약점 원소 공격은 1회에 파괴합니다. 내구도가 0일 때 파괴·방출을 한 번 재생한 뒤 같은 크기의 구슬로 남습니다.",
         hint="위 GIF는 v2의 파괴 과정 비교입니다. 버튼은 손상 반복 동작을 수정한 최신 v3 재생기를 엽니다.",
         scripts=[("assets/items/elements/break-release-v3/animations.json", "정상·손상·파괴·구슬 애니메이션 설정"),
                  ("assets/items/elements/break-release-v3/state-machine.mjs", "3타 / 약점 1타 상태 전이")]),
    dict(id="attack", tag="무속성 · 공격 효과", title="충격탄 · 발사 · 명중 · 약한 넉백",
         image="neutral-attack/neutral-attack-preview.gif", page=None,
         text="무속성 공격 동작과 별도 충격탄·발사·명중 효과를 함께 보는 연출입니다. 낮은 피해와 약한 넉백을 표현하며 피해 5는 미확정 시험값입니다.",
         hint="체력 감소와 넉백은 연출 시안이며 본게임 전투 판정은 아직 연결하지 않았습니다.",
         scripts=[("tools/preview_neutral_attack.py", "공격·발사체·명중 효과 비교 GIF 생성")]),
    dict(id="maps", tag="이동 · 지형 미리보기", title="대기 / 걷기 · 낙하 / 가시 접촉",
         image="obstacle-room/obstacle-room-ingame-preview.png",
         page="obstacle-room/obstacle-room-preview.html",
         text="30×30 기본·장애물 맵의 WASD 이동, 벽 충돌과 캐릭터 대기·걷기를 확인합니다. 장애물 맵에는 플레이어 낙하 후 복귀와 가시 접촉 점멸 시안이 있습니다.",
         hint="위 이미지는 정지 구도입니다. 상세 재생기를 클릭한 뒤 WASD로 움직입니다. 체력·적·전투는 미구현입니다.",
         scripts=[("tools/build_base_room.py", "기본 / 장애물 맵·재생기 생성"),
                  ("tools/base_room_preview.js", "이동·충돌·낙하·가시 접촉 미리보기")]),
]


def main():
    cards = []
    for card in CARDS:
        script_links = "".join(
            f'<li><a href="../../{escape(path)}"><code>{escape(path)}</code></a>'
            f'<span>{escape(label)}</span></li>' for path, label in card["scripts"])
        link = (f'<a class="open" href="{card["page"]}">상세 재생기 열기 ↗</a>'
                if card["page"] else '<a class="open" href="neutral-attack/neutral-attack-preview.gif">원본 GIF 열기 ↗</a>')
        if card["id"] == "maps":
            link += '<a class="secondary" href="base-room/base-room-preview.html">빈 기본 맵 열기 ↗</a>'
        cards.append(f'''<article id="{card['id']}">
<div class="visual"><img src="{embedded(card['image'])}" alt="{escape(card['title'])} 미리보기" loading="lazy"></div>
<div class="body"><div class="tag">{card['tag']}</div><h2>{card['title']}</h2>
<p>{card['text']}</p><p class="hint">{card['hint']}</p><div class="links">{link}</div>
<details><summary>관련 스크립트·설정 보기</summary><ul>{script_links}</ul></details></div></article>''')
    html = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>엘리먼트 이터 · 지금까지 만든 애니메이션</title>
<style>
:root{color-scheme:dark;--bg:#111f1b;--panel:#1b3028;--line:#385348;--text:#f3efdf;--muted:#b5c7bc;--accent:#d7ec9d}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.7 system-ui,'Malgun Gothic',sans-serif}
main{max-width:1400px;margin:auto;padding:48px 28px}header{max-width:1000px;margin-bottom:28px}.eyebrow{font-size:12px;letter-spacing:.14em;color:var(--accent)}h1{font-size:clamp(28px,4vw,46px);line-height:1.28;letter-spacing:-.04em;margin:12px 0 16px}header p{color:var(--muted);margin:8px 0}.chips,nav{display:flex;flex-wrap:wrap;gap:9px;margin:20px 0}.chips span,nav a{border:1px solid var(--line);border-radius:30px;padding:6px 14px;font-size:14px}nav a{color:var(--text);text-decoration:none}nav a:hover{border-color:var(--accent)}.notice{border-left:3px solid var(--accent);padding:12px 18px;background:var(--panel);border-radius:0 12px 12px 0;margin:24px 0 32px;color:var(--muted)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}article{background:var(--panel);border:1px solid var(--line);border-radius:18px;overflow:hidden;scroll-margin-top:22px}.visual{height:350px;display:flex;justify-content:center;align-items:center;background:#14251f;padding:12px}.visual img{max-width:100%;max-height:100%;object-fit:contain;border-radius:5px}.body{padding:24px}.tag{font-size:12px;color:var(--accent);letter-spacing:.04em}h2{font-size:23px;line-height:1.4;margin:8px 0 12px;letter-spacing:-.03em}p{margin:8px 0;color:var(--muted)}.hint{font-size:13px}.links{display:flex;flex-wrap:wrap;align-items:center;gap:14px;margin:20px 0}a{color:var(--accent);text-underline-offset:4px}.open{display:inline-block;background:var(--accent);color:#1b3020;font-size:14px;font-weight:700;text-decoration:none;padding:10px 16px;border-radius:9px}.secondary{font-size:14px}details{border-top:1px solid var(--line);padding-top:14px;font-size:13px}summary{cursor:pointer;color:var(--muted)}ul{list-style:none;padding:0;margin:12px 0 0}li{margin:12px 0}li a{overflow-wrap:anywhere}li span{display:block;color:var(--muted)}code{font-size:12px}footer{margin-top:28px;font-size:13px;color:var(--muted)}
@media(min-width:1100px){#hero .visual{height:500px}#idle .visual{height:500px}}@media(max-width:700px){main{padding:28px 16px}.grid{grid-template-columns:1fr}.visual{height:330px}#hero .visual{height:460px}.body{padding:20px}h2{font-size:21px}}
</style></head><body><main><header><div class="eyebrow">ELEMENT EATER · ANIMATION LIBRARY</div>
<h1>지금까지 만든 애니메이션</h1>
<p>움직이는 미리보기를 한눈에 보고, 상세 재생기에서 방향·원소·공격 상태를 직접 바꿔 보세요.</p>
<div class="chips"><span>캐릭터 6종 · 24개 시트 · 768프레임</span><span>원소 오브젝트 5종</span><span>손상 반복 10종</span><span>2026.11.09 기준</span></div>
<nav aria-label="애니메이션 분류"><a href="#enemies">원소 적</a><a href="#projectiles">투사체</a><a href="#hero">캐릭터</a><a href="#idle">오브젝트 대기</a><a href="#damage">손상 반복</a><a href="#release">파괴·방출</a><a href="#attack">공격 효과</a><a href="#maps">이동·지형</a></nav></header>
<div class="notice">현재는 에셋과 HTML/GIF 미리보기 단계입니다. Python/pico2d 본게임과 R 고유 스킬 애니메이션은 아직 구현하지 않았습니다.</div>
<div class="grid">''' + "\n".join(cards) + '''</div>
<footer>목록의 이미지는 HTML 안에 들어 있어 별도 이미지 파일 없이 표시됩니다. 상세 재생기와 소스 링크는 저장소의 상대 경로를 사용하므로 outputs/와 assets/, tools/의 폴더 구조를 유지해 주세요.</footer>
</main></body></html>'''
    destination = OUT / "index.html"
    destination.write_text(html, encoding="utf-8")
    print(f"생성: {destination.relative_to(ROOT)} ({destination.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
