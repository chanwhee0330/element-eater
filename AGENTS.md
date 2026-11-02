# Project guidance

- This project is Element Eater (엘리먼트 이터), a Korean 2D game course project.
- Read `PROJECT_CONTEXT.md` and `docs/GAME_DESIGN.md` before changing game design or starting implementation.
- The repository currently contains planning artifacts and concept images. Do not describe the game as implemented until runnable source exists.
- Preserve the user's elemental roles: fire damage over time, water self healing, wind knockback, earth terrain creation, lightning multi-target chain attacks.
- The user also confirmed body color and distinguishing appearance changes on ingestion, elemental enemies, and a strict one-to-one attack cycle: water beats fire, fire beats wind, wind beats earth, earth beats lightning, lightning beats water. Non-matching attacks, including same-element attacks, deal zero damage and apply no offensive effects.
- Elemental basic attacks and the original special abilities are separate. Do not accidentally replace water self-healing with its basic attack, or restore the old rule that zero special charges removes the current element.
- Other mechanics and numerical values are initial proposals, not user-confirmed requirements.
- Keep the scope focused on Python/pico2d, five elements, two enemy types and four fixed rooms unless the user changes it.
- Keep project documentation in Korean and use repository-relative paths so both desktop and laptop checkouts work.
- Update `PROJECT_CONTEXT.md` and `docs/ROADMAP.md` when implementation status or significant decisions change.
- Do not commit credentials, local environment files, temporary artifact exports or validation logs. Keep generated public artifacts in `outputs/` and source art in `assets/`.
- Preserve the existing editable PPTX files. Do not replace them with slide screenshots.
