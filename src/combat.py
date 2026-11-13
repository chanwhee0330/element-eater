"""첫 방 전투 초기값. 수치는 사용자 확정값이 아닌 플레이 테스트용 설계안."""
from dataclasses import dataclass


@dataclass(frozen=True)
class CombatTuning:
    spike_damage: int = 10
    player_hp: int = 100
    melee_hp: int = 30
    ranged_hp: int = 40
    neutral_damage: int = 5
    neutral_target_damage: int = 15
    enemy_damage: int = 10
    attack_duration: float = 8 / 12
    attack_event: float = 3 / 12
    player_interval: float = .7
    melee_interval: float = 1.15
    ranged_interval: float = 1.8
    melee_range: float = 1.05
    ranged_range: float = 13
    neutral_speed: float = 7
    neutral_range: float = 4
    enemy_shot_speed: float = 4
    enemy_shot_range: float = 16
    invulnerability: float = .7
    knockback_distance: float = .28
    knockback_seconds: float = .12
    elemental_damage: int = 15
    elemental_speed: float = 8
    elemental_range: float = 6
    heal_amount: int = 20
    lightning_damage: int = 15
    lightning_range: int = 320
    lightning_jump_range: int = 200
    lightning_max_targets: int = 3
    ingest_range: float = 1.25
    ingest_duration: float = 8 / 12
    ingest_event: float = 4 / 12
    # 지형은 이번에도 피해 없는 시각 시안을 유지한다. 상세 피해 정책은 미확정.


@dataclass
class Projectile:
    x: float
    y: float
    dx: float
    dy: float
    owner: str
    speed: float
    remaining: float
    damage: int
    age: float = 0
    element: str = 'neutral'
    active: bool = True


@dataclass
class Feedback:
    x: float
    y: float
    text: str = ''
    enemy_hit: bool = True
    remaining: float = .55
    duration: float = .55
