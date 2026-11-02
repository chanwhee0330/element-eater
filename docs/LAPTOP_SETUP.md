# 노트북에서 작업 이어가기

## 처음 가져오기

1. 노트북에 Git과 사용할 편집기 또는 Codex를 준비합니다.
2. 파일을 둘 위치에서 터미널을 열어 다음을 실행합니다.

```powershell
git clone https://github.com/chanwhee0330/element-eater.git
cd element-eater
```

3. 복제한 `element-eater` 폴더를 편집기나 Codex에서 엽니다.
4. `PROJECT_CONTEXT.md`와 `docs/GAME_DESIGN.md`를 확인합니다.
5. Codex에 다음처럼 요청하면 됩니다.

> PROJECT_CONTEXT.md와 docs/GAME_DESIGN.md를 읽고 엘리먼트 이터 작업을 이어가줘. 현재 기획을 기준으로 다음 작업을 진행해줘.

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

## 현재 실행 상태

게임 코드가 아직 없으므로 지금은 실행할 게임이나 설치할 게임 의존성이 없습니다. PPTX와 PDF, 기획 문서와 컨셉 이미지를 확인하고 수정할 수 있습니다. 첫 프로토타입을 만들 때 Python과 pico2d 설치 및 실행 명령을 이 문서에 추가합니다.

이 저장소에는 원래 대화 전체가 아니라, 이어서 작업하는 데 필요한 기획과 현재 상태를 정리해 두었습니다.
