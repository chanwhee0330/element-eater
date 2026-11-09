# 기획서와 발표 결과물

[근접형·원거리형 원소 적 HTML](previews/elemental-enemies/preview.html): 무속성·물·불·바람·흙·번개의 두 유형, 대기·이동·공격, 4방향·1,152프레임입니다. 같은 몸통을 고정해 조립했고 프레임별 실제 PNG의 보호 영역을 검사했습니다. 원화·시트는 `assets/sprites/enemies/elemental-v1/`, 내장 `image_gen` 전체 생성 프롬프트는 `assets/prompts/elemental-enemy-rigs-v1.json`입니다.

[원소별 기본 공격 투사체 HTML](previews/basic-projectiles/preview.html): 무속성·물·불·바람·흙·번개의 캐릭터 발사와 확대 비행 루프, 방향·수동 발사·자동 시연·속도·일시정지를 확인합니다. 내장 `image_gen` 원화에서 만든 6종·192프레임 투명 PNG/JSON은 `assets/effects/basic-projectiles/v1/`에 보관하며, 원소별 최종 프롬프트는 `assets/prompts/hero-basic-projectiles-v1.json`입니다.

[지금까지 만든 애니메이션 모아보기 HTML](previews/index.html): 캐릭터 6종의 네 동작, 원소 오브젝트 대기·손상·파괴·구슬 방출, 무속성 공격 효과와 이동·장애물 미리보기입니다. 관련 스크립트 링크와 최신 상세 재생기를 함께 제공합니다. 목록의 이미지는 HTML에 내장되며 `python tools/build_animation_gallery.py`로 다시 만듭니다. Python/pico2d 본게임과 R 고유 스킬 애니메이션은 구현 전입니다.

| 폴더 | 파일 |
| --- | --- |
| planning | [상세 기획 PPT 30쪽](planning/엘리먼트_이터_기획서_허찬휘.pptx) |
| presentations/first | [1차 발표 PPT 7쪽](presentations/first/엘리먼트_이터_1차발표_허찬휘.pptx) |
| presentations/first | [90초 발표 대본 PDF](presentations/first/엘리먼트_이터_90초_발표대본_허찬휘.pdf) |
| presentations/first | [1차 발표 영상](presentations/first/2023184037_허찬휘_엘리먼트이터_1차발표영상.mp4) |
| previews/hero-neutral | [주인공 대기·걷기 미리보기 HTML](previews/hero-neutral/hero-neutral-preview.html) · [GIF](previews/hero-neutral/hero-neutral-preview.gif) · [전체 프레임 PNG](previews/hero-neutral/hero-neutral-contact.png) |
| previews/neutral-attack | [무속성 공격·충격탄·약한 넉백 연출 GIF](previews/neutral-attack/neutral-attack-preview.gif) · [공격·효과 전체 프레임](previews/neutral-attack/neutral-attack-contact.png) |

PPT는 편집 가능한 원본으로 보관합니다. 문서 형태의 게임 규칙은 [기획 문서](../docs/design/GAME_DESIGN.md), 방과 보스 설계는 [스테이지 문서](../docs/design/STAGES_AND_BOSS.md)에서 확인합니다.
