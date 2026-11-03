# Project guidance

- This project is Element Eater (엘리먼트 이터), a Korean 2D game course project.
- Read `PROJECT_CONTEXT.md` and `docs/design/GAME_DESIGN.md` before changing game design or starting implementation.
- The repository currently contains planning artifacts and concept images. Do not describe the game as implemented until runnable source exists.
- Preserve the user's elemental roles: fire damage over time, water self healing, wind knockback, earth terrain creation, lightning multi-target chain attacks.
- The user also confirmed body color and distinguishing appearance changes on ingestion, elemental enemies, and a strict one-to-one attack cycle: water beats fire, fire beats wind, wind beats earth, earth beats lightning, lightning beats water. Non-matching attacks, including same-element attacks, deal zero damage and apply no offensive effects.
- Elemental basic attacks and the original special abilities are separate. Do not accidentally replace water self-healing with its basic attack, or restore the old rule that zero special charges removes the current element.
- Other mechanics and numerical values are initial proposals, not user-confirmed requirements.
- The latest scope, confirmed from the user-approved 30-slide design deck, is Python/pico2d, five elements, two regular enemy behavior types, nine regular rooms, one elemental transformation boss room, and elemental environmental puzzles. Read `docs/design/STAGES_AND_BOSS.md` for details.
- Keep project documentation in Korean and use repository-relative paths so both desktop and laptop checkouts work.
- Update `PROJECT_CONTEXT.md` and `docs/development/ROADMAP.md` when implementation status or significant decisions change.
- Do not commit credentials, local environment files, temporary artifact exports or validation logs. Keep generated public artifacts in `outputs/` and source art in `assets/`.
- Preserve the existing editable PPTX files. Do not replace them with slide screenshots.

- Keep design documents in `docs/design/`, plans in `docs/development/`, guides in `docs/guides/`, image prompts in `assets/prompts/`, and editable presentation deliverables in the corresponding `outputs/` subfolder.
- Preserve the sprite atlas PNG/JSON pair and their relative image filename when organizing assets.
