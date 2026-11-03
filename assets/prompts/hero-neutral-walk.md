# 기본 상태 캐릭터 스프라이트 생성 기록

- 결과: [스프라이트 시트](../sprites/hero/neutral/hero-neutral-walk.png), [프레임 데이터](../sprites/hero/neutral/hero-neutral-walk.json).
- 참조: [기본 주인공](../concepts/character-cover.png), [원소별 외형](../concepts/hero-element-forms.png).
- 도구: 내장 이미지 생성 도구 (image_gen), 투명 배경 사용.
- 기준: 기존 character-cover.png의 아이보리 몸, 초록 잎 귀와 hero-element-forms.png의 도트 스타일.
- 기본 무속성 캐릭터만 포함. 원소별 변신 스프라이트는 추후 제작.
- 정확한 생성 프롬프트:

```text
Use case: stylized-concept.
Asset type: production 2D game character sprite sheet, transparent PNG.
Primary request: Turn the existing Element Eater protagonist in the reference artwork into a clean, usable BASE / NEUTRAL STATE four-direction walking sprite sheet. This is an in-game asset, not a poster or concept illustration.
Input images: Image 1 is the reference for the neutral character's identity: warm ivory round body, two green leaf ears on top, tiny rounded arms and feet, large dark mouth, simple cute eyes. Image 2 is a reference ONLY for the project's compact pixel-art style and common body proportions; do not include any of its elemental forms or elemental effects.
Character: one consistent small ivory plant creature, two green leaf ears, dark brown outline, ivory highlights and pale tan underside shadows, dark brown dot eyes, a cheerful open mouth with a small muted coral tongue visible from front. Compact round body with no separate neck, tiny arms and two stubby feet. No clothing, weapons, accessories or elemental effects. Back view shows the plain ivory back and both leaf ears, no face drawn on the back.
Style: crisp, deliberate retro pixel art, limited palette, hard clean pixel clusters, simple readable shading, no blurry edges, no painterly rendering, no 3D, no vector-style smooth contours. Keep silhouette and facial features readable when drawn at 64 x 64 screen pixels. Lighting is constant upper-left.
Layout: exactly 1024 x 1024 pixels; regular invisible 4-column by 4-row grid, exactly 16 sprites, each cell 256 x 256 pixels. Equal spacing, no drawn grid. Each sprite centered horizontally within its cell, entire character including ears and feet inside the cell with substantial transparent padding. The soles in every cell align to y=224 relative to that cell. Character body size, leaf size and ground pivot consistent across all 16 frames.
Rows top to bottom: row 1 faces down toward viewer; row 2 faces left; row 3 faces right; row 4 faces up away from viewer. These are four matching cardinal facings for a top-down dungeon game, slight overhead camera with top of head visible, never a side-scroller character.
Columns left to right in every row: 1 relaxed neutral stance with feet together; 2 walking with first foot forward and opposite arm forward; 3 passing stance with both feet under body, slight one-pixel upward body bounce and leaf sway; 4 walking with other foot forward and opposite arm forward. Four-frame loop, subtle motion. All frames represent the SAME character.
Scene/backdrop: genuinely transparent alpha background everywhere outside the individual sprites, including spaces between frames. No floor, cast shadow, scenery, background color, checkerboard drawn into the image, labels, text, numbers, guide marks, borders, watermarks, extra characters, items, effects or colored glows.
Constraints: exactly 16 complete sprites, 4 equal rows x 4 equal columns. Preserve ivory neutral-state character identity. No water/fire/wind/earth/lightning transformation.
```
