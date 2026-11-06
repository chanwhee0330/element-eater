# 무속성 주인공 뒷모습 수정

## 추가 색상 수정 — 사용자 최종 요청

뒷모습을 정면과 같은 밝은 아이보리색과 초록색으로 맞추고, 뒷면이라는 이유로 어둡게 처리하지 않습니다. 앞선 어두운 뒷면 명암 지시는 이 요청으로 대체합니다. 내장 image_gen을 사용했으며, 원화의 8열×3행과 뒤쪽 동작을 유지합니다.

```text
Use case: precise-object-edit.
Task: COLOR-ONLY correction of an existing production sprite sheet.
Image 1 is the EDIT TARGET: 8 columns x 3 rows of rear-facing idle/walk/attack sprites. Image 2 is the COLOR REFERENCE: use its FIRST/front-facing row, not its bottom rear row.
User request: "Make the back exactly the same color as the front; do not darken it."
Recolor EVERY rear sprite in Image 1 to the same bright creamy IVORY body and fresh bright YELLOW-GREEN leaves as the FRONT sprites in image 2. The target body currently has a dull tan/brown cast and the leaves are dark olive. Remove this extra rear-only darkening. Body should be pale luminous ivory (main fill around #FFF0CA, lit areas around #FFF8E4), with only the same light honey shading on the lower edge as the front. Match the front's brightness, hue and saturation, including arms/heels. Match front leaves' light spring-green tops and midtones; no extra dark olive wash just because this is a rear view. Retain brown outlines and modest local shading to preserve round volume.
HARD invariants: change ONLY body/leaf colors and brightness. Keep ALL 24 silhouettes, anatomy, little occluded arms, alternating heels, leaf shapes/stems, poses, proportions, positions, spacing, 8x3 layout, full canvas framing and animation sequence exactly as image 1. No face on the back, no features added, no redrawn pose, no change to dimensions or crop. Row1 idle8; row2 walk8; row3 attack8. True transparent RGBA background, preserve transparency. No background, floor, cast shadow, fringe, grid, text or decorations. This is recoloring the SAME rear sprite sheet, not generating a new design.
```

- 도구: 내장 image_gen, 투명 RGBA 편집.
- 결과 원화: `assets/sprites/hero/neutral/source/raster/rear-source.png` (8열×3행: 대기·걷기·공격).
- 기존 원화 3장과 최초 뒷모습 시안을 참조해 두 차례 편집했습니다.
- 등 명암·잎 뒷면·몸 앞에 가려진 팔·좌우 뒤꿈치 교차로 화면 위쪽을 향하는 동작을 구분합니다.
- 원화는 그대로 보관합니다. 패킹은 실체 경계에서 6px 여유를 둔 사각 크롭과 균일 리사이즈만 하며 크롭 안의 RGBA를 유지합니다.

## 최초 편집 프롬프트

```text
Use case: precise-object-edit.
Asset type: production transparent RGBA animation source sheet for Element Eater's NEUTRAL hero, REAR VIEW correction.
Input images: Image 1 walk-source.png is the edit target and character/style reference; Image 2 idle-source.png and Image 3 attack-source.png are timing/style references. All have an incorrect bottom row: it is a front body with only the face erased. Replace that anatomy with a true REAR VIEW of the SAME character.
Primary request: output ONE NEW sheet containing ONLY the corrected rear-facing animations, exactly 8 columns by 3 rows, 24 complete sprites on genuine transparent alpha. Rows: idle, walk AWAY FROM CAMERA toward top of screen, attack AWAY FROM CAMERA. No other directions.
Identity invariants: same chubby warm ivory round plant creature, two green leaf ears, tiny round hands and stubby feet, dark brown outlines, soft painted shading, pale tan underside, consistent upper-left lighting. Match existing art rendering and proportions precisely. No new accessories, tail, seam, markings, or elemental effects.
Critical anatomy correction: visibly draw the convex BACK/rump, not the front belly sphere; shoulders/upper back slope away, arms attach forward on the far side and are partially occluded by the back, only outer elbow/hand edges visible. Foot backs/heels show below the rump, with the FAR stepping foot receding upward and largely disappearing behind the body while the near heel lifts toward the camera. Show the backs/undersides and center stems of both green leaves with a subtly different rear silhouette; no front-style belly highlight or hands held on the belly. No face, mouth, eyes, cheeks, or muzzle on the back. Camera is the same elevated 3/4 top-down game camera; preserve round body volume.
Layout: landscape sheet, 2048 x 1024 if possible. Invisible equal 8-column by 3-row grid. Each full sprite centered in its own cell with generous transparent padding. All subjects same scale, about 175 px tall including leaves, about 165px wide, never touching neighbors. No shadows, floor, grid, text, labels, checkerboard, numbers, effects, projectiles.
Row 1 idle frames 0-7: subtle breathing, slight leaf sway, balanced heels and far-side hands mostly hidden, loop.
Row 2 walk frames 0-7: coherent 8-frame WALK AWAY loop. Frame 0 left heel back toward viewer and right foot reaching forward mostly hidden; 1 left heel pushes off; 2 feet pass; 3 right heel begins back swing; 4 right heel fully back toward viewer and left foot forward hidden; 5 right heel pushes off; 6 feet pass opposite; 7 left heel begins back swing. Clear alternating occlusion of feet, restrained opposite arm swing visible on outer edges, slight lateral weight shifts and subtle leaf lag. Body is leaning slightly AWAY in motion, never toward viewer. Frame 7 connects to 0. Do not use eight nearly identical poses or mirrored front walking poses.
Row 3 attack frames 0-7: 0 ready as idle0; 1 compress/windup leaning away; 2 charging with elbows forward hidden; 3 release forward/up away from camera, far-side head subtly leans up, NO mouth on back; 4 small recoil toward camera; 5-6 settle; 7 ready as idle0.
Only redraw the rear view, exactly the existing character style and identity.
```

## 최종 수정 프롬프트

```text
Use case: precise-object-edit.
Edit target: Image 1 is the 8-column x 3-row rear animation sheet to CORRECT. Image 2 is the original full walking sheet for style/character identity only. Keep the same warm ivory spherical leaf-eared hero, dark brown outlines and painted shading. Genuine transparent RGBA background.
Critical correction: This STILL looks like the front with face erased. Make a recognizable 3/4 overhead BACK view. Draw rear shoulders tapering toward a lower, fuller rounded rump. The upper back should lean AWAY toward the top of the cell. Move the bright central round belly highlight to a narrow curved highlight along the LEFT shoulder/back contour; shade the mid-back softly and broadly. No circular belly disk or central white glare spot. Both arms must attach to the FAR/front side and be almost completely hidden by the body: only tiny elbow silhouettes on the sides, never visible palms/round hands stuck on the back. Leaves must show their darker undersides with rear central stems visible; keep the two familiar green leaf shapes, but angle them slightly forward/away rather than an upright front display. Tiny paired heels at rest, single near heel during stride; NO tail, seam, new decoration, visible face or paws on belly.
Keep exact 8-column x 3-row transparent grid with 24 complete sprites, equally sized/centered, substantial empty padding, same body size as the original. Row 1 idle; Row 2 walk AWAY toward screen top; Row 3 attack away. No floor, shadows, colored fringe, halo, text, borders, grid or background.
Fix ROW 2's incorrect foot sequence. It must have one complete coherent 8-frame gait: column 0 LEFT heel clearly behind toward viewer at lower left, RIGHT leg forward mostly hidden behind upper-right rump; column 1 same left heel pushing off/receding, right foot barely visible; column 2 PASSING both feet close under body; column 3 RIGHT heel emerges behind at lower right while LEFT goes forward hidden; column 4 RIGHT heel fully behind at lower right (opposite of column0); column 5 same right heel pushes off/recedes, left foot barely visible; column 6 PASSING opposite phase both close; column 7 LEFT heel starts emerging behind at lower left connecting to column0. Most important: columns 0 and 4 MUST have OPPOSITE feet exposed, and 1 and 5 also opposite; do not draw the left heel in all frames. Raised heels show a SMALL shaded back/sole angle, never a large round disk. Body has subtle alternating weight shift and 2px height bob, leaf secondary motion. Far foot must be occluded, making direction away unmistakable.
Row1 tiny breathing/leaf sway and balanced rear feet. Row3 ready0, lean away/compress1-2, release forward/up3, recoil4, settle5-6, ready7, arms remain behind body throughout. No mouth on back.
Change rear anatomy, rear lighting, leaf perspective and walk sequence as specified; keep identity, paint style, grid and transparent alpha.
```
