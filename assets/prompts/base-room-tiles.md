# 기본 맵 타일 원화 제작

- 도구: 내장 image_gen, 불투명 PNG.
- 원화: `assets/maps/base-room/source/tiles-source.png`.
- 2×2 원화를 64px 타일 4장으로 자르고, 코드에서 정확히 30×30칸으로 배치합니다.
- 원화에는 플레이어가 없으며, 기존 무속성 시트를 높이 1칸으로 별도 배치합니다.

```text
Use case: stylized-concept.
Asset type: a production 2D top-down game TILE TEXTURE ATLAS, opaque square PNG, for the cute ivory leaf-eared hero's ruined garden dungeon.
Output exactly one square image divided into an invisible 2x2 grid of FOUR equally sized SQUARE tiles. Each quadrant is one separate seamless full-bleed tile with zero gutters and no labels. Keep quadrant borders at the exact center of the image.
Upper-left: a single broad gray-beige sandstone floor flagstone, restrained pale warm highlights, thin dark grout on the very outermost edge, light wear, tiny chipped corners. Interior calm and legible.
Upper-right: variant of the SAME square sandstone floor slab, same color/value/scale and perimeter grout, with one subtle thin diagonal crack.
Lower-left: variant of same sandstone floor tile with tiny desaturated moss tufts near two corners. At least 90% empty walking stone surface.
Lower-right: one solid square stone WALL block viewed from above with a slight front-facing lower bevel, chunky raised top, slightly darker cool gray-brown stone, moss only in one corner. Entire square occupied; this is a repeating solid boundary block, not a doorway.
Style: charming hand-painted 2D fantasy dungeon game tile art, clean chunky dark outlines, soft restrained painted light, same visual language as a round cream plant creature; game-ready readable even at 64x64px. Uniform top-down orthographic view, not isometric, no vanishing point. Subdued earthy gray-beige floor, muted olive moss; floor lighter than wall. Tiles must join into a precise square tiled room.
No characters, enemies, items, torches, text, numbers, HUD, water, strong directional cast shadows, perspective floor plane, decorative frame, white gaps, border around the whole atlas, checkerboard, transparency or extra tiles. Four full square texture tiles only, exact 2x2 equal layout.
```
