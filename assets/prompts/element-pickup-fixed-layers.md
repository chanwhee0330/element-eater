# 원소 먹이 고정 본체 보정

- 방식: 내장 image_gen으로 기존 원화의 고정 부분과 동작 부분을 별도 투명 RGBA 레이어로 제작.
- 사용자 수정: 항아리는 수면만, 장작은 불꽃만, 전지는 양옆 스파크만, 바람개비는 중심축·받침대 고정 후 날개만 회전.
- 본체는 동일 PNG를 매 프레임 재사용한다. 프레임별 전체 물체 재생성 원화는 더 이상 물·불·바람·번개의 최종 동작으로 쓰지 않는다.
- 바람은 단일 회전자 원화를 고정 중심으로 15도씩 회전해 24프레임·12fps로 베이크한다. 중심 나무 허브도 매 프레임 같은 픽셀을 복사한다.
- tools/bake_pickup_layers.py가 레이어를 합성하며 모든 보호 픽셀의 RGBA 일치를 검사한다.
- 초기 디자인과 이전 전체 물체 원화는 보관한다.

## water-ripples

편집 대상: assets/items/elements/source/water-source.png

Use case: precise-object-edit. Edit target: the cyan water visible inside the supplied blue jar. Extract ONLY ANIMATED WATER SURFACE REFLECTIONS into a transparent RGBA sprite sheet, no jar or solid surface. Exactly 8 frames, 4 columns x 2 rows, equal square cells on a 2:1 canvas. Each cell has a few pale cyan and white curved glints and a small ripple ring, viewed as a shallow horizontal ellipse from the same slight top-down angle as the reference water surface. The glints are contained in the SAME centered horizontal ellipse width75% cell, height26% cell; keep all marks strictly INSIDE this footprint. The curved glints circulate and the round ripple expands then fades in eight distinct sequential phases for a seamless calm 1-second loop. Sparse marks with translucent feathered pale cyan edges, keep a clear empty center in some phases, not a fully opaque blue pool. Preserve painterly texture. All eight cells use identical framing, center, scale. No ceramic jar, rim, handles, body, base, text, labels, floor, shadow, grid lines, detached droplets, background, huge glow or thick waves. Transparent background is essential. Only the water glints, no other object.

## fire-logs

편집 대상: assets/items/elements/source/fire-source.png

Use case: precise-object-edit. Edit the supplied burning log pickup: REMOVE ALL FLAMES and leave ONLY the exact same three crossed brown wood logs with the same cut ends and warm orange highlights. Preserve the same painterly style, brown outline, slight top-down front view, log arrangement and proportions. No flame tongues anywhere, no yellow fire emerging between logs, no smoke or sparks, no ash pile, no floor, no shadow, no scene. Single isolated stationary bundle of three crossed logs centered on transparent RGBA background with generous padding. Do not add text, labels, a circle, a fire pit or extra logs.

## fire-flames

편집 대상: assets/items/elements/source/fire-idle-source.png

Use case: precise-object-edit. The input is a 4-column 2-row animation sheet of 8 burning-log sprites. Keep the SAME eight flame poses and painterly fire style, but REMOVE THE WOOD LOGS ENTIRELY from every cell. Output exactly eight FLAME-ONLY sprites in 4 columns by 2 rows of equal square cells on a 2:1 transparent RGBA canvas. Match the original eight pose progression: flame sways left, rises, splits, leans right, lowers and recovers. Each flame emerges from the same centered small origin, fixed horizontal baseline at 85% of its cell. Similar scale and same origin in all cells, no camera changes. Orange outer tongues, yellow and ivory inner core, preserve clean dark warm edging and painterly brush texture. No brown wood, no logs, no ground, no shadow, no smoke, no text, no grid lines, no scene. Keep flame tips and sides within each cell. Final frame loops into first. Actual transparency.

## wind-stand

편집 대상: assets/items/elements/source/wind-source.png

Use case: precise-object-edit. Edit target: supplied green pinwheel pickup. REMOVE ONLY THE FOUR GREEN LEAF BLADES completely. Preserve its wooden round CENTER HUB, straight vertical wooden POLE, and round wooden FOOT as a single rigid stationary stand in the exact same painterly style and warm brown colors. The hub stays attached centered over the pole. Keep the original front slight top-down view, round wood hub and round base, no perspective turn. Output one isolated stand with hub on transparent RGBA background, with original empty upper space where the leaves used to be. Keep layout of reference as closely as possible: hub about x50%,y35%, foot centered about x50%,y90%. No leaves or blade fragments at all, no green parts, no extra handle or joint, no movement, no scene, no floor or shadow, no text or marks.

## wind-rotor

편집 대상: assets/items/elements/source/wind-source.png

Use case: precise-object-edit. Edit target: supplied four-green-leaf pinwheel. Extract ONLY THE FOUR LEAF BLADES AND THEIR SMALL ROUND WOODEN CENTER HUB as one flat pinwheel rotor; completely REMOVE the vertical wood pole and the round wood base. Preserve exactly four broad curved leaves, alternating yellow-green and deeper green, vein brushwork, chunky brown edges, warm painterly style and winding arrangement. The small circular wood hub is at the EXACT CENTER of a SQUARE transparent RGBA canvas. All four leaves fit inside an inscribed circle around this hub, ample padding, visually balanced. No stem, no support pole, no pedestal, no shadow, no motion streaks, no arrows, no text, no scene. Single stationary rotor, not a sprite sheet. This rotor will be mechanically rotated around the center hub, so its hub must be clear and centered. Do not change the pinwheel into a flower or add more leaves.

## lightning-sparks

편집 대상: assets/items/elements/source/lightning-source.png

Use case: precise-object-edit. The reference is a battery pickup. Create ONLY ITS SMALL YELLOW ELECTRICAL SPARK ARCS as a transparent RGBA 8-frame idle loop, 4 columns x 2 rows of equal square cells on a 2:1 canvas. There is NO battery visible, NO battery silhouette or black box, and no center lightning-bolt emblem. The entire middle 50% width of EVERY CELL remains completely transparent to leave room for a stationary battery. Tiny painterly yellow jagged arcs flicker ONLY along the left and right sides, around x20% and x80%, y25%-65%. Frame0 very faint left spark,1 small left arc,2 bright upper left arc,3 left fades and right appears,4 bright right arc,5 short lower right arc,6 right fades,7 faint gap to loop into0. Use short readable zigzag segments, warm orange edge and pale yellow core, only restrained local translucent glow. Exact same cell layout and margins for all8; no whole-sheet background, no floor, no shadow, no labels or grid. No large explosions, no detached symbols, no circle aura. Preserve the reference's hand-painted fantasy game style.

