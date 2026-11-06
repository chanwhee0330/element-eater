## 2026-11-06 중심 정렬 수정

발끝 대신 몸통 윤곽을 기준으로 모든 동작/방향을 같은 중심에 맞췄습니다. 귀·발의 비율과 걷기 동작을 유지합니다. 몸통 아래를 자르던 직사각형 발 덮어쓰기는 제거했습니다. 공격·섭취 시작/끝은 idle 0번과 같습니다. 최종 재생성은 `python tools/build_hero_registered.py`입니다.

# 물 원소 주인공

대기·걷기·기본 공격·구슬 먹기 각각 4방향×8프레임, 총 128프레임입니다. 128px 칸·1024×512px 시트·발밑 (64,114), 권장 표시 배율 0.5입니다.

| 동작 | PNG | JSON |
| --- | --- | --- |
| 대기 | [hero-water-idle.png](hero-water-idle.png) | [hero-water-idle.json](hero-water-idle.json) |
| 걷기 | [hero-water-walk.png](hero-water-walk.png) | [hero-water-walk.json](hero-water-walk.json) |
| 기본 공격 | [hero-water-attack.png](hero-water-attack.png) | [hero-water-attack.json](hero-water-attack.json) |
| 구슬 먹기 | [hero-water-ingest.png](hero-water-ingest.png) | [hero-water-ingest.json](hero-water-ingest.json) |

공격·섭취의 첫째·마지막 프레임은 같은 방향 idle 0번과 같습니다. 대기·공격·섭취의 발 하단은 고정하고 걷기는 보행 동작을 유지합니다. 발사체·구슬은 별도 이미지입니다. Space 기본 공격과 R 고유 능력을 구분합니다.

[4방향 비교 GIF](../../../../outputs/previews/hero-elements/previews/water-four-states.gif) · [원화](../elemental-source-v1/water/)

다섯 원소 전체 재생성은 저장소 루트에서 `python tools/build_element_heroes.py`입니다. Python과 Pillow가 필요합니다. 본게임 판정·전투·보유량·원소 전환 연결은 아직 하지 않았습니다.