# 노트북에서 작업 이어가기

## 처음 가져오기

1. 노트북에 Git과 사용할 편집기 또는 Codex를 준비합니다.
2. 파일을 둘 위치에서 터미널을 열어 다음을 실행합니다.

```powershell
git clone https://github.com/chanwhee0330/element-eater.git
cd element-eater
```

3. 복제한 `element-eater` 폴더를 편집기나 Codex에서 엽니다.
4. `PROJECT_CONTEXT.md`와 `docs/design/GAME_DESIGN.md`를 확인합니다.
5. Codex에 다음처럼 요청하면 됩니다.

> PROJECT_CONTEXT.md와 docs/design/GAME_DESIGN.md를 읽고 엘리먼트 이터 작업을 이어가줘. 현재 기획을 기준으로 다음 작업을 진행해줘.

GitHub Desktop을 사용한다면 `File > Clone repository`에서 저장소 URL을 입력해도 됩니다.

공개 저장소는 로그인 없이 복제할 수 있습니다. 수정 내용을 올릴 때는 저장소를 소유한 GitHub 계정으로 인증해야 합니다.

## 매번 작업을 시작할 때

다른 기기에서 올린 최신 변경을 먼저 가져옵니다.

```powershell
git status
git pull --ff-only
```

로컬에 미완료 변경이 있으면 먼저 저장하고 커밋한 뒤 최신 변경을 합칩니다. 충돌이 나면 해당 파일을 확인해 해결합니다.

## 작업을 마친 뒤

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

한 컴퓨터에서 작업을 마치고 `push`한 다음, 다른 컴퓨터에서 `pull`하고 이어갑니다. PPTX는 Git에서 내용을 자동 병합하기 어려우므로 한 기기에서 편집을 끝내고 업로드한 뒤 다른 기기로 옮겨 작업합니다.

## Python 게임 설치와 실행

타이틀과 1·2번 방 Python/pico2d 프로토타입이 있습니다. Windows 64비트 Python 3.11을 준비합니다(실제 검사 Python 3.11.1). 저장소 루트에서 다음을 실행합니다. 가상환경 활성화 없이 실행하므로 PowerShell 실행 정책을 바꿀 필요가 없습니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

이후에는 `run_game.bat`을 더블클릭하거나 마지막 명령을 다시 실행합니다. `.venv`는 PC별로 새로 만들며 Git에 올리지 않습니다. 의존성은 [pico2d 1.5.1](https://pypi.org/project/pico2d/1.5.1/), PySDL2, Windows SDL DLL 패키지이며 버전은 `requirements.txt`에 고정했습니다. 게임 실행에는 Node/Pillow가 필요 없습니다. 다른 폴더에서 `main.py`의 절대 경로로 실행해도 리소스를 찾습니다.

- WASD: 이동. 마지막 이동 방향 유지
- 타이틀: 왼쪽 이어하기/가운데 새게임 시작/오른쪽 종료. 마우스 클릭 또는 좌우/A/D/Tab 선택 후 Enter/Space
- Space: 선택 원소 기본 탄환. 누르고 있으면 반복 공격하며 원소를 소모하지 않음
- F: 파괴된 원천에서 방출된 구슬 섭취. 항아리 자체는 먹지 않음
- Q/E: 보유 원소 선택. 현재 얻을 수 있는 원소는 물
- R: 물 자가 회복. 성공하면 물 1개 소모, 최대 체력에서는 무소모
- Esc: 일시정지·재개. 메뉴에서 W/S 또는 방향키로 계속하기/현재 방 재시작/타이틀로 돌아가기/게임 종료 선택 후 Enter
- 창 X: 종료. 창 포커스를 잃으면 자동 정지하며, 복귀 후 Esc로 재개

첫 방의 큰 구역에 진입하면 근접 2마리가 추격/공격하고 원거리 2마리가 제자리 사격합니다. 적을 전멸시키고 출구에 도달하면 체력을 유지해 두 번째 방으로 이동합니다. 두 번째 방에는 무속성 2·불 2와 물 항아리 2개가 있습니다. 항아리 3타→구슬 F 섭취→물 Space로 불 적 공격/R 자가 회복을 진행합니다. 무속성 적은 모든 공격에 큰 피해(시험값 15), 원소 적은 상성 또는 낮은 무속성 피해(5)를 받습니다. 두 번째 방 출구가 현재 분량의 끝입니다. 사망/클리어 뒤 Enter로 현재 방을 초기화합니다. 다른 원소 획득/R·3번 이후·퍼즐·보스는 미구현이며 낙하/가시는 피해 없는 시안입니다. R로 재시작하지 않습니다.

## 코드 검사

진행은 `saves/continue.json`에 새 게임 시작·2초 간격·일시정지·타이틀 복귀·종료 시 저장합니다. 버전 2는 1/2번 방 위치·HP·적/탄환·공격·원천 손상/구슬·보관함·섭취 중 상태를 복원하며 기존 v1 첫 방 저장도 읽습니다. 사망은 마지막 생존 저장을 보존합니다. 1번 출구는 2번 저장으로 갱신하고 2번 클리어는 비웁니다. 새게임은 기존 진행을 초기화합니다. 저장은 Git으로 옮기지 않으며 손상되거나 지원하지 않는 저장은 이어하기가 비활성화됩니다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/smoke_room_01.py
.\.venv\Scripts\python.exe tools/smoke_title.py
.\.venv\Scripts\python.exe tools/smoke_room_02.py
```

첫 명령은 창 없이 상태·전투·저장을 검사합니다. SDL 검사들은 실제 키 이벤트로 전투/HUD·방 전환·타이틀·저장/이어하기·F/R·손상 1/2의 렌더링 픽셀 변화와 바닥 접점 고정을 확인하고 실행 화면 PNG를 생성합니다. 임시 저장 경로를 사용해 실제 진행을 건드리지 않습니다. 검사 중에는 포커스를 주입하며 별도로 창을 숨겨 실제 포커스 상실 자동 정지도 확인합니다. 아직 노트북 실기기 검증은 하지 않았습니다.

UI는 Windows의 맑은 고딕을 우선 사용하며 설치되지 않은 경우 pico2d에 포함된 한글 글꼴을 사용합니다. 별도 UI 이미지나 글꼴 다운로드는 필요 없습니다.

`smoke_title.py`는 저장 없음/있음 두 타이틀 화면과 비활성 클릭·새게임·앱 재생성 후 이어하기·스테이지 표시·자동 저장·클리어/종료를 검사합니다. 모든 자동 검사는 임시 저장 경로를 사용하므로 사용자 진행을 바꾸지 않습니다.

이 저장소에는 원래 대화 전체가 아니라, 이어서 작업하는 데 필요한 기획과 현재 상태를 정리해 두었습니다.

기획 PPT는 `outputs/planning/`, 1차 발표 PPT·대본·영상은 `outputs/presentations/first/`, 실제 스프라이트는 `assets/sprites/`에서 찾습니다.
