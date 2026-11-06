# 장애물 배치 예시 · 30×30

기존 기본 맵과 같은 **30×30칸**, 플레이어 높이 **1칸**, 1칸 64px를 유지한 장애물 배치 시안입니다. 빈 기본 맵은 [base-room](../base-room/README.md)에 그대로 남겨 비교할 수 있습니다.

| 지형 | 예시 배치 |
| --- | --- |
| 구멍 | 왼쪽 위 5×3칸, 오른쪽 아래 4×4칸의 두 구역 |
| 내부 벽 | 오른쪽 위와 왼쪽 아래의 ㄱ자 엄폐물, 총 20칸 |
| 가시 | 오른쪽과 아래쪽에 각각 4×2칸, 총 두 구역 |
| 플레이어 | 중앙 (15, 15)의 안전 바닥, 기존 밝은 무속성 대기·걷기 시트 |

구멍은 어두운 빈 공간과 끊어진 돌 테두리, 벽은 솟은 돌 블록, 가시는 금속 판과 뾰족한 형태로 구분합니다. 모든 일반 바닥이 안전한 통로로 연결되는 배치입니다. 기본 배치 JSON에는 적·먹이·출구를 넣지 않았고, 별도 원소 미리보기 설정으로 먹이 다섯 종류를 비교합니다.

- [플레이어와 장애물 이름이 있는 예시 화면](../../../outputs/previews/obstacle-room/obstacle-room-scale-preview.png)
- [지도 일부만 보여주는 인게임 구도 시안](../../../outputs/previews/obstacle-room/obstacle-room-ingame-preview.png): 1280×720 화면에 16×9칸과 플레이어 높이 1칸, 간단한 HUD를 배치했습니다. 눈금과 이름표는 없습니다. 실제 게임 화면이 아닌 구도·크기 비교 예시입니다.
- [서버 없이 여는 이동 미리보기](../../../outputs/previews/obstacle-room/obstacle-room-preview.html)
- [원소 5종을 안전 바닥에 놓은 애니메이션](../../../outputs/previews/element-pickups/element-pickups-map.gif) · [확대·재생 조절 HTML](../../../outputs/previews/element-pickups/element-pickups-preview.html): `source/element-pickup-view.json`이 발밑 배치를 정합니다. 실제 1번 방 먹이 구성 변경이나 섭취 구현은 아닙니다.
- [1920×1920 배경 PNG](obstacle-room.png) · [배치·충돌 JSON](obstacle-room.json)
- [64px 칸 2열×3행 타일 시트](obstacle-room-tiles.png)

미리보기는 맵 클릭 후 WASD/방향키로 움직이며, 내부 벽 충돌과 구멍 낙하·안전 위치 복귀, 가시 접촉 점멸을 볼 수 있습니다. 낙하·점멸은 **시각 시안**이며 체력 피해, 적 추락, 전투·넉백 판정과 본게임은 구현 전입니다. 낙하 시간·이동 속도 등도 확정 밸런스가 아닙니다.

## 데이터와 재생성

타일 ID 0~2는 일반 바닥, 3은 벽, 4는 구멍, 5는 가시입니다. 구멍·가시는 이동을 막는 벽 타일로 분류하지 않습니다. 구멍은 `regions`의 직사각형 전체에 원화 한 장을 배치해 내부에 잘못된 돌 테두리 이음새가 생기지 않게 그립니다. 배경 PNG를 쓰면 이 표현이 이미 포함되어 있습니다.

```sh
python tools/build_base_room.py --variant obstacles
python tools/render_ingame_preview.py
python tools/build_element_pickups.py
python tools/render_element_pickups.py
```

`source/recipe.json`이 고정 배치를 정하고 바닥 원화는 기존 기본 맵에서 공유합니다. 구멍과 가시 원화는 내장 image_gen으로 만들었으며 [프롬프트](../../prompts/obstacle-room-assets.md)에 기록했습니다. 코드는 원화의 분리·리사이즈와 맵 조립, 기존 플레이어 배치만 합니다. [장애물 기획](../../../docs/design/OBSTACLES_AND_HAZARDS.md)의 미확정 피해·추락 세부를 최종 규칙으로 확정하지 않습니다.
