# 중심 정렬 이전의 중간 출력

원본 ImageGen 원화에서 잘라 낸 24개 PNG/JSON의 고정 입력입니다. 최종 에셋에 변환을 반복 적용하지 않도록 분리했습니다. 기본형 원화는 `../neutral/source/raster/`, 원소 원화는 `../elemental-source-v1/`에 보존합니다.

최종 재생성: 저장소 루트에서 `python tools/build_hero_registered.py` (Pillow, NumPy 필요).
새 원화로 교체할 때는 기존 `build_hero_sprites.py`, `build_hero_ingest.py`, `build_element_heroes.py`로 만든 중간 PNG/JSON을 이 폴더에 갱신한 뒤 최종 재생성을 실행합니다. 이 중간 출력으로 최종 PNG를 덮어쓰지 않습니다.
