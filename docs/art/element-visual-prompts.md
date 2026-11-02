# 원소 외형과 상성 컨셉 이미지 생성 기록

제작일: 2026년 11월 2일. 제작 방식: 내장 `image_gen` 이미지 생성 도구. 기존 주인공과 화면을 참조해 만들었습니다. 게임의 실제 실행 화면이나 완성된 애니메이션 시트는 아닙니다.

## 주인공 원소별 외형

- 결과: [hero-element-forms.png](../../assets/concepts/hero-element-forms.png)
- 참조: [기존 표지 주인공](../../assets/concepts/character-cover.png)
- 투명 배경을 요청했습니다.
- 최종 프롬프트:

```text
Use case: stylized-concept. Asset type: one wide character appearance comparison sheet for the Korean 2D game 'Element Eater'. Reference image 1 supplies ONLY the established protagonist's identity and pixel-art style, not its eating pose, battery, or surrounding composition. Create ONE clean horizontal sheet containing exactly FIVE evenly spaced, separate, full-body variants of the SAME cute little round blob protagonist, left to right: WATER, FIRE, WIND, EARTH, LIGHTNING. Keep the same round body, tiny arms and feet, cheerful large dark open mouth, dark eyes, proportions, scale, camera, and standing three-quarter facing-right pose in all five. Each must have TWO ear/antenna shapes derived from the original leaf ears. The WHOLE BODY must change to a clearly distinct element color, not just its aura. WATER: cyan-blue soft jelly body, two water-droplet shaped ears, small bubbles and watery highlights. FIRE: orange-red body, two flame-shaped ears, small orange flame tips. WIND: pale leaf-green body, two elongated swept-back leaf/ribbon ears, a few short wind curls. EARTH: warm ochre-brown body, small angular stone-plated patches and two stone-crystal shaped ears, readable rocky silhouette but still the same cute creature. LIGHTNING: vivid golden-yellow body, two zigzag lightning-bolt shaped ears, small electric sparks. Distinct ear silhouettes must identify the element even without relying on body color. Preserve cohesive crisp pixel-art outlines and controlled pixel clusters from the reference; game concept art, not vector, not 3D, not photorealism. Composition: very wide landscape about 3:1, five equal-width columns with generous separation, character feet aligned on one baseline, effects contained entirely within each column, all characters completely visible with safe padding. Transparent alpha background, no solid backdrop, no ground, no shadows outside the characters, no UI, no frames, no objects being held or eaten, no batteries, no extra characters, no arrows, NO text, NO labels, no watermark. This is a concept comparison sheet, not an animation sprite sheet. Make the five body colors and silhouette changes the primary focus.
```

## 물 주인공과 불 속성 적의 전투

- 결과: [gameplay-element-matchup.png](../../assets/concepts/gameplay-element-matchup.png)
- 참조 1: [이전 플레이 화면](../../assets/concepts/gameplay-concept.png)
- 참조 2: [원소별 주인공](../../assets/concepts/hero-element-forms.png)
- 최종 프롬프트:

```text
Use case: precise-object-edit. Edit reference image 1, the pixel-art top-down dungeon game concept, to illustrate the NEW elemental appearance and enemy weakness rules of Element Eater. Reference image 2 supplies the exact five protagonist transformations; use ONLY its blue WATER form here. Preserve the original dungeon stone floor, ruins, moss, top-down camera and overall composition, and keep exactly ONE protagonist at center-left. Replace its ivory body and green leaf ears with the blue water body and two droplet ears from reference 2, same size in scene, visibly BLUE. Replace ALL three original neutral robot enemies with FIRE-element variants: unmistakable orange-red armored bodies, flame-shaped crests and small orange fire particles, still recognizable robot enemies. The blue WATER protagonist is shooting a small blue water elemental projectile that visibly splashes against the nearest orange FIRE enemy. No lightning anywhere, no gold aura on the protagonist. The other fire enemies stand farther right, not connected by any attack. Keep the water jar, logs, wind pinwheel, rocks and battery as edible items in the room, and retain the closed exit gate. Remove ALL old UI panels, all text, all hearts and all icon bars so this is a clean gameplay concept scene with no lettering. Small enemy health bars are allowed. Aspect 16:9 landscape. Crisp cohesive pixel-art, same charming game style, clear contrast between blue water player and orange fire enemies. No duplicate protagonist, no different player forms, no dramatic full-screen effects, no watermark.
```

## 흙 섭취 전후의 외형과 엄폐 지형

- 결과: [earth-form-cover-example.png](../../assets/concepts/earth-form-cover-example.png)
- 참조 1: [이전 엄폐 비교](../../assets/concepts/earth-cover-example.png)
- 참조 2: [원소별 주인공](../../assets/concepts/hero-element-forms.png)
- 최종 프롬프트:

```text
Use case: precise-object-edit. Edit the side-by-side pixel-art before/after dungeon illustration in reference image 1. Preserve its two panels, stone dungeon, rock cover on the LEFT, new three-block continuous earth wall on the RIGHT, enemy positions and projectile blocking events. The LEFT panel is before eating: keep the original ivory protagonist with green leaf ears behind the natural rock cover. The RIGHT panel is after eating the rock: replace ONLY the right-panel protagonist with the EARTH form from reference image 2, warm ochre-brown round body, visible stone-plate patches and two angular rock ears, exactly same small gameplay scale and position. This changed body color and stone ears must be clear against the floor. Also update the robot enemy in BOTH panels to FIRE-element appearance: orange-red armor and small flame crest. Their orange/red projectiles still hit the cover, not the player. Environmental earth walls block projectiles regardless of the attacking enemy element. No other attacks, no damage numbers. The protagonist earth form must remain the same cute round creature, not a humanoid or golem. Keep all other content and the comparative composition intact. Wide landscape approx 2.4:1, no text, no labels, no UI, no extra characters, no watermark.
```
