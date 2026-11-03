# 무속성 주인공 둥근 체형 재제작

2026년 11월 3일 사용자 요청: 첨부 원소 외형처럼 둥글고 귀여운 무속성 시트로 교체.

- 도구: 내장 image_gen, 투명 배경 출력. CLI/API 키는 사용하지 않았습니다.
- 스타일 기준: [사용자 첨부 원본](../concepts/neutral-style-reference.png).
- 원화: [대기](../sprites/hero/neutral/source/raster/idle-source.png), [걷기](../sprites/hero/neutral/source/raster/walk-source.png), [공격](../sprites/hero/neutral/source/raster/attack-source.png).
- 기존 시트는 Git 커밋 `cfc0abd`에서 확인합니다. 걷기·공격 생성에는 새 대기 원화도 참조했습니다.
- 최종화는 원화 RGBA를 유지한 칸 분리·균일 배율·발밑 정렬·아틀라스 조립입니다. 수작업으로 원화의 몸·표정·색을 다시 그리거나 배경을 지우지 않았습니다.
- [재구성 설정](../sprites/hero/neutral/source/raster/manifest.json), [에셋 사용 안내](../sprites/hero/neutral/README.md).

## 대기 최종 프롬프트

```text
Use case: style-transfer.
Asset type: replacement production neutral/base protagonist IDLE sprite sheet for Element Eater.
Input image 1 is the user's elemental character style reference, NOT an edit target. Input image 2 is the old neutral idle sprite sheet to replace; preserve its four-direction/eight-column layout but completely redraw the character with the softness and cuteness of image 1.
PRIMARY CHANGE: the old neutral sprite feels crude and rigid. Match the elemental designs' plump, nearly circular mochi-like body, adorable large happy upside-down-U eyes, generous open smiling mouth with a coral tongue, rosy oval cheeks, big rounded mitten arms growing naturally out of the body, very short rounded feet blended into the lower body. Avoid separate ring-like hands, dangling pebble feet, angular polygon leaves, hard rectangular shadow bands, or a thin side profile.
NEUTRAL IDENTITY: warm ivory/cream body, two soft broad green leaf ears, dark warm-brown outline, cream highlights and pale golden underside shadows. No colored elemental body, magic, fire, water, rocks, lightning, wind swirls, clothes, objects, or glow. Two leaf ears have rounded, gently curved silhouettes and clear soft leaf veins.
STYLE: polished detailed pixel-art illustration exactly like the reference, fine cohesive pixel clusters and rounded stepped curves, soft dimensional shading, upper-left lighting, clean dark contour. NOT a primitive 32px or 64px procedural icon; each sprite should have the visual detail of a hand-drawn 192px game character. NOT vector art, 3D rendering, a fuzzy painting, or coarse blocks.
LAYOUT: exactly 8 columns by 4 rows = 32 complete sprites on a wide sheet, ideally 2048x1024. Equal invisible cells and lots of transparent clearance. Row 1 DOWN/front, row 2 LEFT three-quarter profile, row 3 RIGHT three-quarter profile, row 4 UP/back. Side bodies must retain the same plump round volume; front cheeks and the open mouth should remain visible in three-quarter view. Back view has no face.
IDLE MOTION: eight subtle continuous idle keyframes left to right: relaxed; gentle inhale; growing breath; soft peak inhale; relaxed; gentle exhale; settle; return near first pose. Tiny delayed leaf sway, barely rising shoulders, feet planted. Same body size, consistent anatomy and lighting, fixed ground line in each row, no camera movement. Do not morph character design between frames.
BACKGROUND: genuinely transparent alpha everywhere outside the sprites and between cells. No cast shadow, background color, checkerboard pixels, scenery, grids, text, labels, frame numbers or watermark. Never crop ears or feet. Only the 32 neutral sprites.
```

## 걷기 최종 프롬프트

```text
Use case: style-transfer.
Asset type: production WALK sprite sheet for Element Eater's redesigned neutral protagonist.
Input image 1 is the new neutral IDLE art and the exact character-design/style reference. Input image 2 is the old walking sheet, used ONLY for its 8-column/4-row arrangement and intended walking direction. Do not preserve the old coarse pixel drawing. Input image 3 is the user's elemental-form illustration, used only for polished round cuteness.
Redraw image 2 as the SAME warm-ivory leaf-eared character in image 1: very plump near-circular mochi body, broad soft curved green leaf ears, big happy curved eyes, generous open smile and coral tongue, round pink cheeks, large softly rounded mitten arms and tiny connected stubby feet. Match image 1's exact ivory palette, soft upper-left light, warm-brown outline and lush green leaf shading. Side views must be chubby three-quarter views, never flat or narrow. No elemental effects, clothing, props or colored body variants.
STYLE: beautifully finished detailed pixel-art illustration, refined small pixel clusters and smooth stepped curves like image 1. Avoid coarse primitive 64px geometry, ring outlines on detached hands, dangling pebble feet, harsh rectangular shading, thin legs, vector art, 3D rendering, blur.
LAYOUT: exactly 8 equal columns by 4 equal rows = 32 sprites. Wide 2:1 canvas, ideally 2048x1024. Row 1 DOWN/front, row 2 LEFT three-quarter, row 3 RIGHT three-quarter, row 4 UP/back with no face. Keep the same camera, body scale, broad silhouette, head/leaf proportions and ground pivot throughout. Generous fully transparent clearance around every complete sprite.
WALK cycle left to right in EACH row: 0 first foot contact / 1 down with small squash / 2 passing with first foot lifting / 3 up pose / 4 opposite foot contact / 5 down / 6 opposite passing / 7 up returning smoothly to first foot contact. Make the two feet and counter-swinging arms clearly alternate, with gentle lively body bounce and soft lagging leaf sway. Feet remain under the body, not disconnected circles. No exaggerated jumps, running, sliding sideways, or changing size/anatomy.
TRANSPARENCY: actual alpha background, including all gaps. No checkerboard pattern, colored matte, cast shadow, floor, borders, labels, numbers, text, background, extra sprites or watermark. No cropped ears or feet.
```

## 공격 최종 프롬프트

```text
Use case: style-transfer.
Asset type: production neutral/base protagonist ATTACK sprite sheet for Element Eater.
Input image 1 is the exact new neutral character and style to match. Input image 2 is the old 8-column/4-row attack sheet, used ONLY for layout and attack staging, NOT its coarse drawing style.
Create the SAME charming warm ivory/cream round leaf-eared creature as image 1 in 32 attack poses. Match its big nearly circular mochi body, broad curved green leaves, warm-brown contour, soft golden underside shading, large happy arc eyes, pink oval cheeks, open laughing mouth and coral tongue, rounded attached mitten arms and very short attached feet. Maintain full round volume in left/right three-quarter views. Keep the adorable face proportions. No elemental colors or magic, no weapon, no projectile baked into frames.
STYLE: polished detailed pixel-art illustration matching image 1, with tiny cohesive pixel clusters, smoothly stepped round contours and soft dimensional upper-left light. Not coarse primitive 64px art, not detached ring hands or pebble feet, not thin profile, not vector art, 3D or blurry painting.
LAYOUT: exactly 8 columns by 4 rows, 32 complete sprites on a wide 2:1 transparent sheet, ideally 2048x1024. Row 1 DOWN/front. Row 2 LEFT three-quarter. Row 3 RIGHT three-quarter. Row 4 UP/back, no face on the back. Equal invisible cells, consistent body scale and feet ground line. Keep at least 10% clear transparent padding on every side of EVERY frame, especially above both leaf tips. No cropped anatomy or overlapping cells.
ATTACK timing left to right for EACH row:
0 relaxed smiling ready pose, matching idle.
1 gentle crouch, rounded cheeks beginning to puff, small pursed O mouth, arms tuck toward body.
2 peak windup with puffed cheeks and a small O mouth, leaves lag backwards; body stays chubby and only slightly squashes.
3 clear spit release: big O-shaped open mouth, arms move forward a little, body leans towards its facing direction; this is the projectile emission frame.
4 soft recoil backwards, mouth still open, leaves follow through.
5 mouth returns toward happy smile and arms settle.
6 almost relaxed.
7 relaxed idle pose closely matching frame 0.
For UP/back views express the same windup, forward lean, recoil and recovery with body, arms and leaves, without adding a face. Feet stay grounded with a stable pivot; do not jump.
TRANSPARENCY: actual alpha background with clean warm-brown edges. No cast shadows, floor, checkerboard, colored matte/fringe, glowing halo, scenery, labels, text, grid, numbers, watermark or extra character. Preserve the reference character identity across all frames.
```

