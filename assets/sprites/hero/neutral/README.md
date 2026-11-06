# 기본 무속성 주인공: 대기·걷기·공격

둥근 아이보리 몸, 두 초록 잎 귀와 작은 팔다리를 가진 기본형입니다. 현재 시트는 내장 `image_gen`으로 만든 원화를 RGBA 그대로 잘라 정렬한 것입니다. 이전 pixelfx 시안 코드는 `source/legacy/`에 보관합니다.

2026년 11월 3일, 뒷모습이 정면에서 얼굴만 지운 자세처럼 보인다는 피드백에 따라 위쪽 방향을 다시 그렸습니다. 팔은 몸 앞쪽에 가려지고, 잎 뒷면과 줄기가 보이며, 걷기는 앞서 나가는 발이 몸에 가려지고 뒤꿈치가 좌우로 교차합니다. 추가 요청에 따라 뒷면의 어두운 갈색·올리브색 명암은 제거하고 몸과 잎을 정면과 같은 밝은 아이보리색·초록색으로 맞췄습니다. 대기·걷기·공격 모두 이 색을 사용하며, 뒷면이라는 이유로 어둡게 표현하지 않습니다.

| PNG · JSON | 구성 | 재생 |
| --- | --- | --- |
| [idle PNG](hero-neutral-idle.png) · [JSON](hero-neutral-idle.json) | 4방향 × 대기 8프레임 | 4fps, 반복 |
| [walk PNG](hero-neutral-walk.png) · [JSON](hero-neutral-walk.json) | 4방향 × 걷기 8프레임 | 10fps, 반복 |
| [attack PNG](hero-neutral-attack.png) · [JSON](hero-neutral-attack.json) | 4방향 × 공격 8프레임 | 12fps, 한 번 |

- 시트는 **1024×512px**, 칸은 **128×128px**, 8열×4행입니다. 총 96프레임입니다.
- 행 순서는 아래(정면) / 왼쪽 / 오른쪽 / 위(뒷면)이며 각 행을 왼쪽부터 재생합니다.
- 투명 배경이며 발밑 기준점은 칸 왼쪽 위 기준 **(64, 114)**입니다.
- 권장 표시 배율은 **0.5배**입니다. 화면에서는 64×64px 칸에 해당합니다. 원화의 부드러운 경계는 보간 확대를 사용합니다.
- 아래·왼쪽·오른쪽 시트의 이미지 픽셀, 재생 속도와 기준점은 뒷모습 수정에서 유지했습니다.

## 미리보기

[전체 애니메이션 HTML](../../../../outputs/previews/hero-neutral/hero-neutral-preview.html)은 서버 없이 열 수 있습니다. 재생·일시정지, 속도와 기준점 표시를 지원합니다. [전체 GIF](../../../../outputs/previews/hero-neutral/hero-neutral-preview.gif), [대기·걷기 프레임](../../../../outputs/previews/hero-neutral/hero-neutral-contact.png), [공격 프레임](../../../../outputs/previews/hero-neutral/hero-neutral-attack-contact.png)도 있습니다.

뒷모습 수정은 [비교 GIF](../../../../outputs/previews/hero-neutral/hero-neutral-rear-before-after.gif)와 [8프레임 비교](../../../../outputs/previews/hero-neutral/hero-neutral-rear-before-after.png)에서 확인합니다. 비교 왼쪽/위가 수정 전, 오른쪽/아래가 수정 후입니다.

## 원화와 다시 만들기

원화는 [source/raster/](source/raster/)의 `idle-source.png`, `walk-source.png`, `attack-source.png`이며, 위쪽 방향만 [rear-source.png](source/raster/rear-source.png)의 대기·걷기·공격 3행으로 대체합니다. [manifest.json](source/raster/manifest.json)이 칸, 배율, 프레임 속도와 방향별 대체를 정합니다. 생성 도구는 원화의 도형·색을 그리지 않고 칸 분리, 사각 크롭, 균일 리사이즈와 발밑 정렬을 합니다. 원본 RGBA는 보관하고 크롭 안의 알파는 변경하지 않습니다.

Python과 Pillow가 있는 환경에서 저장소 루트에서 실행합니다.

```sh
python tools/build_hero_sprites.py
python tools/preview_neutral_attack.py
```

첫 명령이 PNG/JSON, HTML/GIF와 전체 프레임 미리보기를 만듭니다. 두 번째 명령은 현재 주인공으로 [무속성 공격 연출 GIF](../../../../outputs/previews/neutral-attack/neutral-attack-preview.gif)를 갱신합니다. 수정 전 시트가 있는 폴더를 `--rear-before-dir 경로`로 지정하면 뒷모습 비교 PNG/GIF도 생성합니다. 일반 빌드는 기존 비교 자료를 덮어쓰지 않습니다. [제작 프롬프트](../../../prompts/hero-neutral-rear.md)에 내장 도구와 최종 수정 지시를 기록했습니다.

## 공격과 발사체 연결

`attack_down/left/right/up`은 0~7번을 한 번 재생한 뒤 idle로 복귀합니다. 0·7번은 같은 방향의 idle 0번과 동일합니다. 준비 0~2, 발사 3, 반동 4, 복귀 5~7이며 **3번 진입(0.25초)에 한 번만 발사체를 생성**합니다.

JSON의 `muzzlePixelsTopLeft`를 발사 위치로 사용합니다. 위쪽 발사체는 주인공 뒤에 그립니다. 낮은 피해·약한 넉백 규칙(피해 5는 미확정 시험값)과 효과는 [무속성 효과 안내](../../../effects/neutral/README.md)를 참고합니다. 실제 게임 판정·연동은 구현 전입니다.

## pico2d 좌표

JSON의 `frame`은 왼쪽 위, `pico2dClip`은 왼쪽 아래 기준입니다. `opaqueBoundsInCell`은 확인용 가시 범위이며 충돌 판정에 사용하지 않습니다. 각 `sourcePose`는 실제 사용한 원화 파일·행·열을 기록합니다.

발밑 좌표 `(gx, gy)`, 배율 `s`일 때 그릴 중심은 `(gx, gy + 50*s)`, 크기는 `(128*s, 128*s)`입니다. 권장 0.5배에서는 중심이 `(gx, gy+25)`, 크기는 64×64입니다.

```python
animation = atlas['animations'][f'{state}_{direction}']
raw_index = int(state_elapsed * animation['fps'])
index = raw_index % 8 if animation['loop'] else min(raw_index, 7)
c = atlas['frames'][animation['frames'][index]]['pico2dClip']
sheet.clip_draw(c['left'], c['bottom'], c['width'], c['height'],
                gx, gy + 50 * scale, 128 * scale, 128 * scale)
```

이 코드는 에셋 연동 예시입니다. 실행 가능한 게임과 원소 변신·섭취·피격 동작은 아직 구현하지 않았습니다.
