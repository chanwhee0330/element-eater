# Project guidance

- This project is Element Eater (엘리먼트 이터), a Korean 2D game course project.
- Read `PROJECT_CONTEXT.md` and `docs/design/GAME_DESIGN.md` before changing game design or starting implementation.
- The repository currently contains planning artifacts and concept images. Do not describe the game as implemented until runnable source exists.
- Preserve the user's elemental roles: fire damage over time, water self healing, wind knockback, earth terrain creation, lightning multi-target chain attacks.
- The user also confirmed body color and distinguishing appearance changes on ingestion, elemental enemies, and a strict one-to-one elemental attack cycle: water beats fire, fire beats wind, wind beats earth, earth beats lightning, lightning beats water. Non-matching elemental attacks, including same-element attacks, deal zero damage and apply no offensive effects.
- The user later confirmed neutral basic attacks: they deal zero damage but slightly knock enemies back regardless of element. Keep this explicit neutral exception separate from blocked elemental attacks and from wind's strong knockback. Knockback distances and timings remain proposals; game combat is not implemented yet.
- Latest user-confirmed controls: WASD movement, Q previous held type, E next held type, R skill, F ingest, Space basic attack. Aim in the last movement direction with no mouse aiming. Restart is in the Esc pause menu, not R.
- Latest user-confirmed inventory: eaten elements stack as counts by type. Q/E select a held type; Space does not consume it. Each successfully activated R skill consumes one unit of its cast element. Exhausted types cannot be selected; no held types means neutral. This supersedes the old single-held-element, three-special-charges and zero-charge-persistence rules. Failed skill activations do not consume a unit in the current proposal.
- Keep elemental basic attacks and special abilities separate: water Space attacks and water R self-healing are distinct. The selected stored type controls current appearance and HUD; already-created effects retain their cast element.
- Other mechanics and numerical values are initial proposals, not user-confirmed requirements.
- The latest scope, confirmed from the user-approved 30-slide design deck, is Python/pico2d, five elements, two regular enemy behavior types, nine regular rooms, one elemental transformation boss room, and elemental environmental puzzles. Read `docs/design/STAGES_AND_BOSS.md` for details.
- Keep project documentation in Korean and use repository-relative paths so both desktop and laptop checkouts work.
- Update `PROJECT_CONTEXT.md` and `docs/development/ROADMAP.md` when implementation status or significant decisions change.
- Do not commit credentials, local environment files, temporary artifact exports or validation logs. Keep generated public artifacts in `outputs/` and source art in `assets/`.
- Preserve the existing editable PPTX files. Do not replace them with slide screenshots.

- Keep design documents in `docs/design/`, plans in `docs/development/`, guides in `docs/guides/`, image prompts in `assets/prompts/`, and editable presentation deliverables in the corresponding `outputs/` subfolder.
- Preserve the sprite atlas PNG/JSON pair and their relative image filename when organizing assets.
