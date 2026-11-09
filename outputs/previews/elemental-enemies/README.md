# 원소 적 애니메이션 미리보기

- `preview.html`: 무속성+5원소 근접형/원거리형의 대기·이동·공격, 4방향 비교. 전체 12종 보기, 속도·일시정지, 프레임 넘기기·슬라이더, 몸통 크기·중심 기준선과 원거리 발사 시연을 제공합니다.
- `melee.gif`, `ranged.gif`: 유형별 무속성과 다섯 원소 × 세 동작 비교. `*-still.png`는 정지 이미지입니다.

HTML은 적 시트 36개, 별도 투사체 6개, 움직이는 대체 GIF 2개를 직접 포함합니다. 파일 하나로 열 수 있고, 스크립트 실행이 제한된 뷰어에는 GIF가 표시됩니다.

원화·PNG/JSON·고정 몸통과 부품 마스크는 `assets/sprites/enemies/elemental-v1/`, 내장 `image_gen` 생성 프롬프트는 `assets/prompts/elemental-enemy-rigs-v1.json`에 보관합니다. 저장소 루트에서 `python tools/build_elemental_enemies.py`로 재생성하고 `--validate-only`로 최종 PNG 1,152프레임을 검사합니다. Pillow·NumPy가 필요합니다.

몸통은 프레임마다 이동·회전·확대하지 않습니다. 발광 RGB와 팔다리만 움직이며, 보호 영역의 픽셀이 최종 PNG에서도 같은 위치에 있는지 검사합니다. 현재는 에셋·연출 시안으로 Python/pico2d AI·전투 판정은 미구현입니다.

무속성 원화 2종의 내장 `image_gen` 프롬프트는 `assets/prompts/neutral-enemy-rigs-v1.json`에 있습니다. 무속성 근접형·원거리형 6시트·192프레임을 추가했으며 기본 선택은 무속성입니다.
