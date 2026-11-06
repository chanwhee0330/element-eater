# 원소 먹이 동작 재조정

- 방식: 내장 image_gen으로 흙의 고정 돌·작은 돌과 전지의 중앙 표시 소등 원화를 분리 제작.
- 불: 기존 불꽃 원화를 재사용하되 장작을 먼저 그리고 불꽃을 앞에 합성. 불꽃 밑동은 칸 내부 (64, 84) 부근 장작 윗면에 고정한다.
- 흙: 뒤의 큰 돌·오른쪽 이끼 돌은 한 장으로 고정, 왼쪽 아래 돌 한 장만 8단계로 살짝 들고 기울인다.
- 번개: 케이스·단자·옆 줄은 동일 원화로 고정, 중앙 번개 모양의 위치와 형상을 유지한 마스크 안에서 소등/점등을 보간한다. 양옆 스파크도 유지한다.
- 설정: assets/items/elements/source/layers/layer-recipe.json

## earth-fixed-rocks

편집 대상: assets/items/elements/source/earth-source.png

Use case: precise-object-edit. Edit target is this three-rock earth pickup. REMOVE ONLY THE SMALL FRONT-LEFT ROCK entirely. Keep the large rear ochre rock and the wide front-right rock with its small moss patch as the SAME two rocks, same faces/cracks/colors/outline and same view. Reveal the missing lower-left area of the big rear rock naturally where the small rock covered it. Preserve the exact painterly fantasy-game style, warm yellow-brown lighting, dark brown chunky outline. No animated motion, no particles, no dust, no other small stones. Two stationary rocks only. Keep reference camera and arrangement as closely as possible, front-right mossy rock fixed relative to big rear rock. Isolated single asset on true transparent RGBA background, no floor, no shadow, no text, no grid.

## earth-small-rock

편집 대상: assets/items/elements/source/earth-source.png

Use case: precise-object-edit. Extract ONLY THE SMALL FRONT-LEFT ROCK from the supplied three-rock pile as a single isolated rock on transparent RGBA. Preserve its rounded angular silhouette, ochre brown faces, warm upper-left highlights, thin branching crack and dark brown outline, same slight top-down front view and hand-painted texture. REMOVE the big rear rock and the entire mossy front-right rock. No moss on this small rock. No extra pebbles, dust, floor, shadow or background. Single exact same front-left small rock, generous padding, centered; no redesign, no text, no grid. It will be gently lifted as a separate rigid layer.

## lightning-off

편집 대상: assets/items/elements/source/lightning-source.png

Use case: precise-object-edit. Edit the supplied battery pickup by TURNING OFF ONLY THE LARGE CENTRAL LIGHTNING-BOLT EMBLEM on the front panel. The zigzag emblem stays in exactly the same shape/position but becomes dark charcoal brown, a recessed unlit engraving with a subtle amber edge, absolutely no yellow light or glow in the central bolt. IMPORTANT invariants: keep the entire battery body, perspective, brass corner caps, single top terminal, two bright yellow vertical side charge strips, colors, textures, outlines, scale and proportions identical. The side strips remain bright; only the center bolt switches off. Same painterly fantasy game style, same light direction. Single battery on true transparent RGBA, no floor, no shadow, no sparks, no scene, no text, no extra symbols. This is the off state of the SAME battery.

