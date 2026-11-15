# 1~6번 방 입체 석재

`masonry-atlas.png`는 1~6번 방에서 공통으로 사용하는 2×2 재질 아틀라스입니다. 왼쪽 위는 바닥 돌, 오른쪽 위는 벽돌, 왼쪽 아래는 벽 덮개, 오른쪽 아래는 보라색 러너입니다. 내장 image_gen에 승인된 UI 시안을 색감과 재질 참고로 제공해 제작했습니다.

`src/isometric.py`는 각 방의 타일 JSON에서 바닥, 벽, 가시와 낭떠러지의 면을 생성합니다. 바닥은 따뜻한 색으로 밝히고, 벽은 어두운 청회색 윗돌·벽돌 입면과 밝은 모서리로 표시합니다. 벽과 바닥이 맞닿는 곳에는 짧은 그림자를 그립니다. 지형과 캐릭터는 타일 좌표에 맞춰 표시합니다. [1~6번 방 실행 화면](../../../outputs/previews/element-acquisition/terrain-contrast-01-06.png)

## 생성 프롬프트

Use case: stylized-concept, production 2D game texture atlas.
Use the supplied Element Eater screenshot ONLY as a material, color palette and painting style reference. Produce one new SQUARE opaque image, a precise 2x2 texture atlas of four flat orthographic surfaces. No characters, words, UI, overhead scene, perspective, sprites, borders between quadrants, separators, empty padding, torch objects, or typography. Each of the four 50%-by-50% quadrants extends fully edge-to-edge. This image is sampled as four materials by a real isometric game renderer. Do not draw the textures as diamond tiles; they must be face-on flat squares.
Top left: one single large flat floor paver stone, dusty warm lilac-gray #857080, lightly worn subtle mottling and small chips, fine shaded beveled lip around this ONE square slab. The surface is low contrast, charcoal-purple thin grout at its outer edges, no inner grid. 
Top right: a flat vertical wall of five horizontal staggered rows of rough-hewn violet gray #665a70 rectangular masonry blocks, thin charcoal grout, subtle chipping and gentle face texture. Rows run horizontally and repeat cleanly vertically and horizontally.
Bottom left: one flat large stone coping cap, warm smoky purple #8f7d89, worn bevel, finer pale slate marks, small chipping. Dark outer edge only, no center grid.
Bottom right: overhead orthographic view of a single square muted plum carpet tile, antique gold narrow linear ornament running along both vertical sides, central region remains solid deep violet textured fabric. Top and bottom must connect seamlessly, no end trim, no words.
Soft, painterly 2D dungeon art, low saturated purple-lavender stone, fine tactile texture, no highlights near white, gentle neutral diffuse light with no baked shadow cast outside each material. Workable legibility for cream-green player and blue pottery. Exact equal quadrants.
