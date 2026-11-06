# pixelfx 사용법

pixelfx는 코드로 픽셀 이펙트를 만들고 PNG 스프라이트 시트와 JSON으로 내보내는 도구입니다. Codex에서 이펙트를 찾아 수정하거나 새로 만들 때 사용합니다. 게임의 피해 판정이나 원소 능력 자체를 구현하는 도구는 아닙니다.

## 이 PC에 준비한 것

- Codex 개인 스킬: `~/.codex/skills/pixelfx`
- 실행 본체: 이 프로젝트와 같은 상위 폴더의 `../pixelfx`
- 확인한 버전: pixelfx 0.3.0, 원본 커밋 `a84159688af3ca37a4be05a0d422b94451b2e24e`
- Node v24.22.1에서 불꽃 효과 렌더, 투명 PNG·JSON 출력과 자체 검사를 확인했습니다.
- 설치 확인 결과는 본체의 `records/setup-check/fire/torch/`에 있습니다.

스킬은 **설치 후 다음 메시지부터** 사용할 수 있습니다. 스킬 목록에 나타나지 않으면 Codex를 다시 실행합니다.

## 가장 쉬운 방법: 채팅으로 요청

Codex 메시지 앞에 `$pixelfx`를 붙이고 원하는 효과와 출력 형식을 적습니다.

```text
$pixelfx 엘리먼트 이터의 불 속성 공격에 쓸 작은 불꽃 효과를 만들어줘.
투명 PNG 스프라이트 시트와 JSON으로 내보내고 프레임 미리보기도 보여줘.
```

```text
$pixelfx 물 속성 자가 치유에 쓸 파란 회복 효과를 만들어줘.
둥근 주인공 발밑에서 물결과 작은 입자가 올라오게 해줘.
```

```text
$pixelfx lightning/chain-lightning을 참고해서 세 적을 잇는 번개 효과를 만들어줘.
우리 게임은 현재 약점이 맞는 적에게만 공격 효과를 적용해야 해.
```

크기, 색, 길이, 반복 여부를 함께 적으면 원하는 결과에 가까워집니다. 예를 들어 `64px 정도`, `연두색`, `0.5초`, `반복 없음`, `타격 순간만 밝게`처럼 요청할 수 있습니다. 새 효과는 프레임을 렌더해 확인하고 수정하는 과정을 거칩니다.

## 직접 실행하는 방법

아래 명령은 Node.js 18 이상이 PATH에 있는 터미널을 기준으로 합니다. Codex는 번들 Node를 사용할 수 있습니다. 일반 터미널에서 `node`를 찾지 못하면 Codex에 위 채팅 방식으로 요청하거나 Node 실행 환경을 준비합니다.

`element-eater` 루트에서 본체 폴더로 이동합니다.

```powershell
cd ..\pixelfx
```

효과 검색:

```powershell
node tools/list.mjs fire
node tools/list.mjs heal
node tools/list.mjs lightning
```

불꽃 프레임 미리보기와 투명 PNG·JSON 출력:

```powershell
node tools/render.mjs fire/torch --sheet
node tools/check.mjs fire/torch
```

결과는 `records/fire/torch/`에 저장됩니다.

| 파일 | 용도 |
| --- | --- |
| contact.png | 여러 프레임을 한 번에 보는 미리보기 |
| torch.png | 게임에서 사용할 투명 배경 스프라이트 시트 |
| torch.json | 프레임 위치, 재생 시간, fps, 반복 여부와 기준점 |

`fire/torch` 설치 시험 결과는 60프레임, 프레임당 72×120px, 30fps의 반복 효과였습니다. 기본 출력 위치와 구분하려고 시험 결과는 `records/setup-check/`에 따로 저장했습니다.

## 움직임 미리보기

[공식 갤러리](https://patch-gg.github.io/pixelfx/)에서 기존 효과를 움직이는 상태로 볼 수 있습니다. 로컬 본체 폴더에서는 다음 명령으로 갤러리를 실행합니다.

```powershell
node tools/serve.mjs
```

브라우저에서 `http://localhost:8080/gallery/`를 열고, 종료하려면 터미널에서 Ctrl+C를 누릅니다.

GIF와 MP4 파일을 만들려면 FFmpeg가 추가로 필요합니다. 이 PC에서는 현재 FFmpeg를 PATH에서 찾지 못했으며, PNG·JSON 출력은 FFmpeg 없이 동작합니다.

## pico2d에 가져오는 방식

최종 선택한 효과는 프로젝트의 `assets/effects/<원소 또는 분류>/<효과 이름>/` 아래에 PNG와 JSON을 함께 둡니다. 현재 설치 시험은 pixelfx 본체 안에서만 했으며 게임에 효과를 연결한 상태는 아닙니다.

- JSON `frames`의 영역과 `duration`을 읽어 애니메이션을 재생합니다.
- `meta.pixelfx`의 `fps`, `loop`, `pivot`을 함께 확인합니다.
- pixelfx 프레임은 위쪽 기준 좌표입니다. pico2d의 클리핑 아래 좌표는 `시트 높이 - frame.y - frame.h`로 변환합니다.
- 기존 주인공 atlas JSON과 형식이 다르므로 pixelfx JSON에 맞는 로더를 구현합니다.
- 주인공 몸에 붙는 회복·화상 효과는 원본의 기본 인체 템플릿 대신 우리 둥근 캐릭터의 크기와 모양에 맞춰 조정합니다.
- 시각 효과와 게임 판정은 분리합니다. 원소 공격은 상성이 틀리면 피해와 공격 효과를 막습니다. 사용자가 추가한 무속성 충격탄은 적 원소와 관계없이 낮은 피해와 약한 넉백을 허용하는 별도 예외입니다. 피해 5는 미확정 시험값입니다.
- 원본 효과를 프로젝트에서 채택할 때 upstream의 LICENSE와 NOTICE도 확인하고 필요한 고지를 함께 보관합니다.

## 노트북에서도 사용하려면

스킬과 본체는 이 PC에 설치한 도구이므로 게임 저장소를 복제하는 것만으로 개인 스킬까지 설치되지는 않습니다. 노트북 Codex에서 다음처럼 요청합니다.

```text
https://github.com/patch-gg/pixelfx 의 skills/pixelfx를 Codex 스킬로 설치하고,
pixelfx 본체도 element-eater와 같은 상위 폴더에 받아서 PNG·JSON 출력을 확인해줘.
```

원본 문서: [pixelfx README](https://github.com/patch-gg/pixelfx), [스킬 사용 지침](https://github.com/patch-gg/pixelfx/blob/main/skills/pixelfx/SKILL.md).
