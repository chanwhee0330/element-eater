# 장애물 예시 맵 원화

- 도구: 내장 image_gen, 불투명 PNG.
- 구멍 원화: `assets/maps/obstacle-room/source/pit-source.png`.
- 가시 원화: `assets/maps/obstacle-room/source/spikes-source.png`.
- 바닥과 벽은 기존 기본 맵 타일을 공유합니다. 실제 30×30 배치와 기존 플레이어는 코드로 조립합니다.

## 구멍

```text
Use case: stylized-concept.
Asset type: a single production top-down 2D dungeon PIT prop texture, opaque square PNG, for a hand-painted ruined sandstone garden game.
Draw exactly ONE square opening where the floor is missing, seen directly from above with a slight visible inner cliff face. The pit fills almost the entire square canvas. A thin irregular chipped gray-beige sandstone rim on the outer 6-9 percent, then jagged fractured stone walls descending into a nearly black deep desaturated blue-gray void. It must clearly read as missing ground one could fall into, not a puddle, rug, crater with a floor, lava, portal or painted black floor tile. Keep the center empty and very dark with only subtle vertical rock detail on the inner rim. No visible bottom.
Match a cute hand-painted fantasy dungeon: warm beige-gray stone flagstone floor, muted olive moss only tiny patches at the rim, chunky dark outlines, controlled soft shading, readable at small game scale. Orthographic top-down, square footprint, not isometric. Entire outermost edge is matching sandstone so the prop can be placed on a sandstone tilemap. No transparent padding, no perspective room, no surrounding scene, characters, enemies, spikes, ladders, bridges, items, text, numbers, grid, UI or effects. One square pit only, centered and full-bleed.
```

## 가시

```text
Use case: stylized-concept.
Asset type: one production 2D top-down dungeon SPIKE TRAP tile texture, opaque square PNG.
Exactly one square floor trap plate filling the canvas, viewed from the same orthographic top-down camera as a hand-painted sandstone dungeon. A 3-by-3 cluster of NINE short sharp steel pyramidal spikes protrudes from one dark desaturated gray iron plate, each spike with a clear pale metallic pointed highlight and a dark shaded side so they look dangerous and raised. Small rivets at plate corners. Very thin chipped warm gray-beige sandstone border at the very edge, matching a calm beige stone floor. Steel spikes should be noticeably lighter and cooler than the beige stone floor; no blood.
Style: readable chunky hand-painted fantasy game art, soft painted shading with clean dark outlines, slight upper-left light, not photorealistic, not isometric. The whole plate fits in the square with no margin or background scene. No characters, weapons, plants, decorative emblem, text, labels, numbers, HUD, grid, floor perspective, extra tiles or other objects. One square spike trap tile only, full-bleed.
```
