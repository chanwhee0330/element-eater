# 무속성 충격탄과 공격 효과

기본형 주인공이 입에서 뱉는 작은 아이보리색 충격탄입니다. 불·물·바람·흙·번개 색이나 장식은 없으며 주인공의 아이보리·갈색 테두리와 어울리는 팔레트로 pixelfx에서 제작했습니다.

| 파일 | 크기와 재생 |
| --- | --- |
| [정지 충격탄 PNG](projectile/neutral-projectile.png) | 32×32px, 오른쪽 방향 첫 프레임 |
| [이동 시트](projectile/neutral-projectile-sheet.png) · [JSON](projectile/neutral-projectile-sheet.json) | 32px 칸, 256×128px, 방향별 8프레임, 12fps 반복 |
| [발사 시트](muzzle/neutral-muzzle-sheet.png) · [JSON](muzzle/neutral-muzzle-sheet.json) | 32px 칸, 256×128px, 방향별 8프레임, 16fps 한 번 |
| [명중 시트](impact/neutral-impact-sheet.png) · [JSON](impact/neutral-impact-sheet.json) | 48px 칸, 384×192px, 방향별 8프레임, 16fps 한 번 |

행은 아래 / 왼쪽 / 오른쪽 / 위, 열은 시간 순서입니다. 기준점은 각 칸 중앙이며 `pico2dClip`을 그대로 사용할 수 있습니다. 명중·발사 시트의 마지막 7번 프레임은 투명하고 종료 후 효과를 제거합니다. 이동 시트는 투사체가 사라질 때까지 반복합니다. 원본 PNG는 투명 배경이며 최근접 보간을 사용합니다.

[주인공 공격 시트](../../sprites/hero/neutral/hero-neutral-attack.png)의 3번 프레임(0.25초)에 발사 위치에서 이동 탄환 1개와 발사 효과를 생성합니다. 첫 적이나 벽 충돌 때 탄환을 제거합니다. 적에게 맞을 때 작은 명중 효과와 낮은 피해·약한 넉백을 함께 적용하는 기획입니다. 연출 GIF에는 체력 100→95와 짧은 밀림을 표시하며 피해 5는 시험값입니다. 실제 게임 판정은 아직 구현하지 않았습니다.

최신 사용자 확정 규칙은 **적 원소와 관계없이 낮은 피해 + 기존 약한 넉백 유지**입니다. 무속성 피해 5는 미확정 시험값이며 원소 약점 배율을 적용하지 않습니다. 같은 원소를 포함한 상성 불일치 원소 공격은 피해·넉백을 모두 차단합니다. 일반 적 12px, 보스 4px·0.1초 등은 미확정 시험값이며 [게임 기획](../../../docs/design/GAME_DESIGN.md)을 기준으로 조정합니다.

원본은 [source/neutral-fx.mjs](source/neutral-fx.mjs), 내보내기는 [tools/render_neutral_attack.mjs](../../../tools/render_neutral_attack.mjs)입니다. Node와 별도 pixelfx 체크아웃은 에셋을 다시 만들 때만 필요하며, 게임에서는 PNG와 JSON을 읽습니다. 피해·넉백 시험값의 제작 원본은 [원화 manifest](../../sprites/hero/neutral/source/raster/manifest.json)의 `neutralCombat`이며 현재/이전 내보내기 도구 모두 이를 읽습니다.

[공격 연출 GIF](../../../outputs/previews/neutral-attack/neutral-attack-preview.gif) · [프레임 미리보기](../../../outputs/previews/neutral-attack/neutral-attack-contact.png)
