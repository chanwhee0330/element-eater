# 기본 무속성 주인공: 대기·걷기·공격

2026년 11월 3일, 사용자의 요청으로 기존 이미지 생성 걷기 시트를 **pixelfx로 직접 그린 픽셀 애니메이션**으로 교체했습니다. 아이보리 몸, 두 초록 잎 귀, 웃는 눈과 큰 입, 작은 팔다리를 유지합니다. 걷기의 첫 장을 대기로 쓰던 방식에서 대기 전용 애니메이션을 분리했습니다.

사용자의 옆모습 피드백을 반영해 좌우 몸통의 가로 지름을 31px에서 38px로 넓히고 세로 비율과 곡선 명암, 얼굴·팔·다리 연결을 보정했습니다. 좌우 대기·걷기에 모두 반영했으며 [수정 전후 비교](../../../../outputs/previews/hero-neutral/hero-neutral-side-before-after.png)에서 확인할 수 있습니다.

| 파일 | 구성 | 재생 속도 |
| --- | --- | --- |
| [hero-neutral-idle.png](hero-neutral-idle.png) · [JSON](hero-neutral-idle.json) | 4방향 × 대기 8프레임, 숨쉬기와 잎 흔들림 | 4fps, 2초 반복 |
| [hero-neutral-walk.png](hero-neutral-walk.png) · [JSON](hero-neutral-walk.json) | 4방향 × 걷기 8프레임, 발 교차·몸 반동·팔과 잎 흔들림 | 10fps, 0.8초 반복 |
| [hero-neutral-attack.png](hero-neutral-attack.png) · [JSON](hero-neutral-attack.json) | 4방향 × 공격 8프레임, 준비·볼 부풀리기·발사·반동·복귀 | 12fps, 약 0.667초, 한 번 재생 |

- 시트 한 장은 **512 × 256px**, 각 칸은 **64 × 64px**, 8열 × 4행입니다. 세 시트 총 96프레임입니다.
- 행 순서는 아래(정면) / 왼쪽 / 오른쪽 / 위(뒷면)입니다. 각 행을 왼쪽에서 오른쪽으로 재생합니다.
- 배경은 투명하며 배경색, 격자, 글자와 바닥 그림자는 게임용 PNG에 포함하지 않습니다.
- 모든 프레임의 발밑 기준점은 칸 내부 왼쪽 위 기준 **(32, 58)**입니다. 걷기의 몸 반동과 들린 발은 의도한 동작이며 게임 좌표를 흔들지 않습니다.
- 기본 표시 배율은 **1배**입니다. 기존 1254px 시트용 0.25배와 4열 설정을 새 시트에 사용하지 않습니다. 확대할 때는 정수 배율과 최근접 보간을 사용합니다.
- 대기는 idle PNG/JSON의 `idle_down` 등, 걷기는 walk PNG/JSON의 `walk_down` 등에서 읽습니다. 이전 walk JSON의 단일 프레임 idle 태그는 새 대기 시트로 옮겼습니다.

## 미리보기

[움직이는 미리보기 HTML](../../../../outputs/previews/hero-neutral/hero-neutral-preview.html)은 인터넷이나 서버 없이 브라우저에서 열 수 있습니다. 재생·일시정지, 속도 변경과 기준점 표시를 지원합니다. [전체 프레임 보기](../../../../outputs/previews/hero-neutral/hero-neutral-contact.png)와 [움직이는 GIF](../../../../outputs/previews/hero-neutral/hero-neutral-preview.gif)도 있습니다.

공격은 [충격탄·넉백 연출 GIF](../../../../outputs/previews/neutral-attack/neutral-attack-preview.gif)와 [공격·효과 전체 프레임](../../../../outputs/previews/neutral-attack/neutral-attack-contact.png)에서 확인합니다. 미리보기의 적은 설명용 더미입니다.

## 공격과 발사체 연결

`attack_down`, `attack_left`, `attack_right`, `attack_up`은 0~7번을 한 번 재생하고 idle로 복귀합니다. 준비 0~2, 발사 3, 반동 4, 복귀 5~7입니다. **3번 프레임 진입(0.25초)에 투사체를 한 번만 생성**합니다. 그릴 때마다 중복 생성하지 않습니다.

JSON의 `muzzlePixelsTopLeft`는 방향별 발사 위치입니다. 발밑 기준점과 같은 좌표 변환을 사용합니다. 위쪽 공격은 투사체를 주인공 뒤에 그리며 나머지 방향은 앞에 그리는 연출 초기안입니다. 실제 투사체 이동·피해·충돌은 구현 전입니다.

[무속성 효과 안내](../../../effects/neutral/README.md)에 정지 충격탄 PNG, 이동·발사·명중 시트와 프레임 JSON이 있습니다. 사용자가 확정한 규칙은 **피해 0과 약한 넉백**입니다. 거리·속도는 [게임 기획](../../../../docs/design/GAME_DESIGN.md)의 초기값을 참고합니다.

## pico2d에서 읽기

JSON의 `frame`은 왼쪽 위 기준이고 `pico2dClip`은 왼쪽 아래 기준입니다. pico2d의 `clip_draw(left, bottom, width, height, cx, cy, draw_width, draw_height)`에는 `pico2dClip` 값을 사용합니다. `opaqueBoundsInCell`은 확인용 가시 영역이며 충돌 영역으로 사용하지 않습니다.

발밑 게임 좌표가 `(gx, gy)`, 표시 배율이 `s`일 때 모든 프레임의 그릴 중심은 `(gx, gy + 26*s)`, 그릴 크기는 `(64*s, 64*s)`입니다. 일반식은 `cx = gx + (w/2 - px)*s`, `cy = gy + (py - h/2)*s`입니다.

```python
# sheet: 해당 상태의 PNG를 load_image로 읽은 객체
# atlas: 같은 이름의 JSON을 읽은 딕셔너리
animation = atlas['animations'][f'{state}_{direction}']
raw_index = int(state_elapsed * animation['fps'])
index = raw_index % len(animation['frames']) if animation['loop'] else min(raw_index, len(animation['frames']) - 1)
frame = atlas['frames'][animation['frames'][index]]
c = frame['pico2dClip']
sheet.clip_draw(c['left'], c['bottom'], c['width'], c['height'],
                gx, gy + 26 * scale, 64 * scale, 64 * scale)
```

위 코드는 연동 예시입니다. 에셋 렌더링과 메타데이터를 확인한 단계이며 실제 게임 실행·연동은 아직 하지 않았습니다. 원소 변신, 섭취·피격 동작은 포함하지 않습니다.

## 코드로 다시 만들기

원본은 [source/hero-neutral.mjs](source/hero-neutral.mjs), 내보내기는 [tools/render_hero_sprites.mjs](../../../../tools/render_hero_sprites.mjs)입니다. Node 18 이상과 프로젝트 옆의 pixelfx 0.3.0 체크아웃을 사용합니다. 게임 실행에는 Node나 pixelfx가 필요하지 않고 최종 PNG/JSON만 필요합니다.

저장소 루트에서:

```sh
node tools/render_hero_sprites.mjs --check
node tools/render_neutral_attack.mjs --check
```

다른 위치의 pixelfx를 쓰면 `--pixelfx 경로`를 추가합니다. 이 명령은 두 시트, 두 JSON, 전체 프레임 PNG와 자체 포함 HTML을 생성합니다. GIF는 최종 PNG를 Pillow로 조립한 별도 배포용 미리보기입니다. `--out ../pixelfx/records/element-eater/draft --contacts`는 정식 에셋을 덮어쓰지 않고 시안을 확인하는 방법입니다.

두 번째 명령은 공격 시트와 무속성 효과 3종을 내보냅니다. 원본은 [source/hero-attack.mjs](source/hero-attack.mjs)입니다. `--draft ../pixelfx/records/element-eater/attack-draft --contacts`로 시험 출력할 수 있습니다. 공격 GIF는 Pillow가 있는 Python에서 `python tools/preview_neutral_attack.py`로 조립합니다. 공격·효과 16개 방향 조합은 3차례 검토 후 pixelfx 검사 16개 모두 통과했습니다.

제작은 3차례 렌더·검토·수정했습니다. 최종 8개 애니메이션은 pixelfx 검사에서 모두 통과했으며 캔버스 밖 그리기, 반복 연결, 비결정성 경고가 없었습니다. [기존 이미지 생성 기록과 교체 안내](../../../prompts/hero-neutral-walk.md)도 보관합니다. 이전 파일 자체는 Git 이력에서 확인할 수 있습니다.
