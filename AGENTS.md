# Project guidance

- This project is Element Eater (엘리먼트 이터), a Korean 2D game course project.
- Read `PROJECT_CONTEXT.md` and `docs/design/GAME_DESIGN.md` before changing game design or starting implementation.
- 현재 저장소에는 Python/pico2d의 타이틀·1/2번 방 실행 코드가 있습니다. 물 획득/물 공격/물 R 회복은 구현했고, 나머지 원소 획득/R·3번 이후 방·보스는 아직 미구현입니다. 아래 에셋 제작 당시의 미구현 기록보다 이 최신 상태를 우선합니다.
- Preserve the user's elemental roles: fire damage over time, water self healing, wind knockback, earth terrain creation, lightning multi-target chain attacks.
- 원소 적에 대한 1대1 상성은 물→불→바람→흙→번개→물입니다. 같은 원소를 포함한 나머지 원소 조합은 피해/공격 효과를 차단합니다. 섭취 후 몸 색/구분 외형이 바뀌는 규칙은 유지합니다.
- 최신 사용자 확정(2026-11-10): **무속성 적은 무속성 및 다섯 원소 공격 모두에 큰 피해를 받습니다.** 앞선 물→무속성 낮은 피해안과 무속성 공격의 일률적인 낮은 피해안을 대체합니다. 무속성 기본 공격은 원소를 가진 적에게는 낮은 양의 피해·약한 넉백을 유지합니다. 무속성 적 큰 피해 15, 낮은 피해 5는 시험값이며 확정 수치가 아닙니다. 약한 넉백은 무속성 기본 공격에만 붙이고 바람의 강한 넉백과 구분합니다. 차단된 원소 공격은 넉백/추락을 유발하지 않습니다.
- Latest user-confirmed controls: WASD movement, Q previous held type, E next held type, R skill, F ingest, Space basic attack. Aim in the last movement direction with no mouse aiming. Restart is in the Esc pause menu, not R.
- Latest user-confirmed inventory: eaten elements stack as counts by type. Q/E select a held type; Space does not consume it. Each successfully activated R skill consumes one unit of its cast element. Exhausted types cannot be selected; no held types means neutral. This supersedes the old single-held-element, three-special-charges and zero-charge-persistence rules. Failed skill activations do not consume a unit in the current proposal.
- Keep elemental basic attacks and special abilities separate: water Space attacks and water R self-healing are distinct. The selected stored type controls current appearance and HUD; already-created effects retain their cast element.
- Other mechanics and numerical values are initial proposals, not user-confirmed requirements.
- 사용자가 장애물로 구멍·낭떠러지, 벽, 가시를 제안했으며 플레이어와 적 모두 구멍에 떨어질 수 있어야 합니다. 피해량·복귀 방식·일반 적과 보스의 추락 결과·가시 피해 대상은 초기안 또는 미확정입니다. `docs/design/OBSTACLES_AND_HAZARDS.md`를 읽고, 상성이 틀려 차단된 원소 공격이 넉백이나 추락을 유발하지 않도록 합니다. 빈 기본 맵은 유지하며 `assets/maps/obstacle-room/`의 별도 30×30 예시에 구멍·내부 벽·가시를 배치했습니다. 미리보기의 플레이어 낙하 복귀·가시 접촉 점멸은 시각 시안이고 체력·적·전투와 본게임 판정은 미구현입니다.
- The latest scope, confirmed from the user-approved 30-slide design deck, is Python/pico2d, five elements, two regular enemy behavior types, nine regular rooms, one elemental transformation boss room, and elemental environmental puzzles. Read `docs/design/STAGES_AND_BOSS.md` for details.
- Keep project documentation in Korean and use repository-relative paths so both desktop and laptop checkouts work.
- Update `PROJECT_CONTEXT.md` and `docs/development/ROADMAP.md` when implementation status or significant decisions change.
- Do not commit credentials, local environment files, temporary artifact exports or validation logs. Keep generated public artifacts in `outputs/` and source art in `assets/`.
- Preserve the existing editable PPTX files. Do not replace them with slide screenshots.

- Keep design documents in `docs/design/`, plans in `docs/development/`, guides in `docs/guides/`, image prompts in `assets/prompts/`, and editable presentation deliverables in the corresponding `outputs/` subfolder.
- Preserve the sprite atlas PNG/JSON pair and their relative image filename when organizing assets.

- Latest user-confirmed acquisition change (2026-11-06): attack elemental source objects to progressively damage them, then ingest their released elemental orbs with F. Never directly ingest the jar/logs/pinwheel/rock/battery. Water jars crack, fire dies down, wind blades tear, rocks and battery shells break. Preserve stored-element inventory and skill consumption. The user confirmed exactly three non-weakness hits (including same element and neutral) or one weakness hit to destroy SOURCE OBJECTS. Persist both damage states until the next attack. Play break/release once at zero durability, then persist the orb. All released orb types must have equal displayed diameter (96px in the v2 preview). This object rule does not change blocked nonmatching attacks against enemies. Latest assets are under assets/items/elements/break-release-v2/; the preview is not implemented Python/pico2d combat.

- Damage-idle animation regression fix (v3): intact, damaged1 and damaged2 must each keep playing their own looping idle sheet until the next attack. Never replace a damaged idle with one static destruction frame or let its loop end/hide the sprite. Keep water ripples, reduced flames, torn rotor rotation, small-rock motion and electric pulses alive in both damage stages. Use assets/items/elements/break-release-v3/ and verify actual rendered pixel changes after the first AND second non-weakness attacks; state persistence alone is not sufficient.

- Keep hit shake, but after it settles the intact/damaged1/damaged2 item must return to its original physical root. Register each damage loop against the intact fixed base and keep one transform across its frames; never recenter on animated flame, water drops or rotor extrema. Preserve FrameDelta first-frame/backwards-time guards so an Invalid timestep exception cannot terminate all animation.

- Neutral ingestion assets now exist as hero-neutral-ingest.png/JSON (four directions, eight frames each), rebuilt separately with tools/build_hero_ingest.py. Preserve exact idle frame 0 at ingestion start/end and original foot-band pixels. Orbs stay separate; the rear view has no face and draws the orb behind the body. The 12fps/frame-4 consume event is a proposal, and gameplay/inventory/transformation integration is not implemented.

- Five elemental hero forms now have idle/walk/Space-basic-attack/ingest sheets, each 4 directions x 8 frames, 20 new sheets/640 frames; neutral included totals 24/768. Read assets/sprites/hero/ELEMENTAL_ANIMATIONS.md. Rebuild with tools/build_element_heroes.py from elemental-source-v1/. Preserve each element body color and distinguishing ears in every facing/state, fixed (64,114) pivots, idle endpoints and stationary foot bands (walking feet still animate). Projectiles/orbs remain separate. These are assets/previews only; do not describe R special-ability sprites or Python/pico2d gameplay as implemented.

- Latest hero center fix: use tools/build_hero_registered.py for final 24-sheet builds from registration-source-v1. Register by torso silhouette, never the currently extended foot or ear. Preserve complete pose pixels; do not overwrite the lower torso with a rectangular idle foot band. This supersedes earlier exact-foot-band instructions. Keep exact idle attack/ingest endpoints and real alternating walk feet. Verify actual exported pixel centers, not metadata pivots alone.

- Hero preview HTML must be self-contained: embed all 24 atlases and six orbs using standalone_hero_preview.py, and keep the embedded animated fallback visible until live canvas draws successfully. Do not reintroduce relative image dependencies.
