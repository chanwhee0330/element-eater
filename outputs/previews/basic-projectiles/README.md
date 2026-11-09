# 기본 공격 투사체 미리보기

- `preview.html`: 이미지 18개와 움직이는 대체 GIF를 내장한 단독 실행 HTML. 무속성+5원소 캐릭터 발사, 4방향, 수동 발사(Space), 자동 시연, 일시정지, 재생 속도와 확대 비행 루프.
- `projectiles.gif`: 6종의 비행 루프를 한 화면에서 비교.
- `preview-still.png`: 비교 화면의 정지 이미지.

원화·시트·설정은 `assets/effects/basic-projectiles/v1/`, 전체 생성 프롬프트는 `assets/prompts/hero-basic-projectiles-v1.json`에 있습니다. 내장 `image_gen`으로 원화를 제작했습니다. 저장소 루트에서 `python tools/build_basic_projectiles.py`로 다시 만듭니다(Pillow·NumPy 필요).

Space 기본 공격용 시각 시안이며, R 고유 능력과 Python/pico2d 본게임 전투 판정은 별도입니다. 크기·속도·12fps·3번 프레임 발사는 초기값입니다.
