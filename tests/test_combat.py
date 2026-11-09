"""공격 타이밍, 충돌, 체력, 적 공격, 승패와 초기화의 전투 시나리오."""
import unittest
from src.room import Room
from src.combat import Projectile


def step(room, seconds, keys=()):
    for _ in range(round(seconds * 120)):
        room.update(set(keys), 1/120)


def quiet_room():
    room = Room()
    # AI를 켜지 않는 시작 섬에 표적을 놓아 플레이어 탄환만 독립 검사한다.
    room.player.x, room.player.y, room.player.facing = 8, 19, 'right'
    for e in room.enemies:
        e.active = False
    enemy = room.enemies[0]
    enemy.active = True
    enemy.x, enemy.y = 10, 19
    return room, enemy


class CombatTests(unittest.TestCase):
    def test_attack_event_fires_once_then_hit_and_slight_knockback(self):
        room, enemy = quiet_room()
        room.start_attack(room.player)
        step(room, .24)
        self.assertFalse(room.projectiles)
        step(room, .03)
        self.assertEqual(len(room.projectiles), 1)
        step(room, .5)
        self.assertEqual(enemy.hp, 15)
        self.assertAlmostEqual(enemy.x, 10+room.tuning.knockback_distance)
        self.assertFalse(room.projectiles)

    def test_attack_retains_cast_direction_while_player_changes_facing(self):
        room, _ = quiet_room()
        room.start_attack(room.player)
        step(room, .27, {'w'})
        self.assertEqual(room.player.facing, 'up')
        shot = room.projectiles[0]
        self.assertEqual((shot.dx, shot.dy), (1, 0))
        self.assertEqual(room.player.attack_facing, 'right')

    def test_wall_stops_projectile_before_target(self):
        room, enemy = quiet_room()
        room.player.x, room.player.y, room.player.facing = 10, 8.5, 'up'
        enemy.x, enemy.y = 10, 5.5
        room.start_attack(room.player)
        step(room, .6)
        self.assertFalse(room.projectiles)
        self.assertEqual(enemy.hp, enemy.max_hp)

    def test_one_bullet_hits_first_target_only(self):
        room, first = quiet_room()
        other = room.enemies[1]
        other.active = True
        other.x, other.y = 11, 19
        room.start_attack(room.player)
        step(room, .8)
        self.assertEqual(first.hp, 15)
        self.assertEqual(other.hp, 30)

    def test_projectile_range_and_no_friendly_fire(self):
        room, enemy = quiet_room()
        enemy.x = 14
        room.start_attack(room.player)
        step(room, 1)
        self.assertEqual(enemy.hp, 30)
        self.assertEqual(room.player.hp, 100)
        self.assertFalse(room.projectiles)

    def test_lethal_hit_updates_count_exit_and_clear_requires_exit(self):
        room, enemy = quiet_room()
        room.damage(enemy, 30)
        self.assertEqual(enemy.hp, 0)
        self.assertFalse(enemy.active)
        self.assertTrue(room.exit_open)
        self.assertIsNone(room.outcome)
        room.player.x = room.data['plannedExit']['x']
        room.player.y = room.data['plannedExit']['y']
        step(room, .02)
        self.assertEqual(room.outcome, 'clear')

    def test_melee_windup_can_be_dodged(self):
        room = Room()
        room.player.x, room.player.y = 5.5, 10.25
        enemy = room.enemies[0]
        self.assertTrue(room.start_attack(enemy))
        self.assertEqual(room.player.hp, 100)
        room.player.x = 3
        step(room, .3)
        self.assertEqual(room.player.hp, 100)

    def test_melee_hit_invulnerability_prevents_simultaneous_stack(self):
        room = Room()
        room.player.x, room.player.y = 5.5, 10.25
        step(room, .35)
        self.assertEqual(room.player.hp, 90)
        self.assertFalse(room.damage(room.player, 10))
        self.assertEqual(room.player.hp, 90)

    def test_neutral_hit_does_not_cancel_enemy_attack(self):
        room = Room()
        enemy = room.enemies[0]
        room.start_attack(enemy)
        room.damage(enemy, 5, (1, 0))
        self.assertEqual(enemy.attack_elapsed, 0)
        self.assertEqual(enemy.hp, 25)

    def test_ranged_enemy_telegraphs_and_fires_when_line_clear(self):
        room = Room()
        room.player.x, room.player.y = 5.5, 7
        step(room, .2)
        self.assertFalse(room.projectiles)
        step(room, .12)
        self.assertTrue(any(s.owner == 'enemy' for s in room.projectiles))
        step(room, 1)
        self.assertLess(room.player.hp, 100)

    def test_ranged_enemy_does_not_fire_through_central_wall(self):
        room = Room()
        room.player.x, room.player.y = 10, 9
        for enemy in room.enemies:
            if enemy.kind == 'melee':
                enemy.active = False
            else:
                enemy.x, enemy.y = 10, 4.5
        step(room, 1)
        self.assertFalse(room.projectiles)

    def test_enemy_projectile_wall_collision_and_hit(self):
        room, _ = quiet_room()
        room.player.x, room.player.y = 10, 9
        room.projectiles.append(Projectile(10, 5.5, 0, 1, 'enemy', 20, 10, 10))
        step(room, .5)
        self.assertEqual(room.player.hp, 100)
        self.assertFalse(room.projectiles)
        room.projectiles.append(Projectile(10, 8.5, 0, 1, 'enemy', 8, 10, 10))
        step(room, .1)
        self.assertEqual(room.player.hp, 90)

    def test_knockback_can_drop_enemy_and_cannot_cross_wall(self):
        room, enemy = quiet_room()
        enemy.x, enemy.y = 5.1, 19
        room.damage(enemy, 5, (-1, 0))
        step(room, .2)
        self.assertGreater(enemy.falling, 0)
        step(room, 1)
        self.assertFalse(enemy.active)
        room, enemy = quiet_room()
        enemy.x, enemy.y = 10, 8.25
        room.damage(enemy, 5, (0, -1))
        step(room, .2)
        self.assertGreaterEqual(enemy.y, 8.2)

    def test_death_stops_combat_and_restart_restores_everything(self):
        room, enemy = quiet_room()
        room.projectiles.append(Projectile(8, 19, 1, 0, 'hero', 7, 4, 5))
        room.damage(room.player, 100)
        self.assertEqual(room.outcome, 'dead')
        self.assertFalse(room.projectiles)
        before = room.elapsed
        step(room, 1, {'attack'})
        self.assertEqual(before, room.elapsed)
        room.reset()
        self.assertIsNone(room.outcome)
        self.assertEqual(room.player.hp, 100)
        self.assertEqual(room.remaining_enemies, 4)
        self.assertTrue(all(e.hp == e.max_hp and e.attack_elapsed < 0 for e in room.enemies))
        self.assertFalse(room.projectiles)
        self.assertFalse(room.feedback)

    def test_held_space_respects_cooldown(self):
        room, enemy = quiet_room()
        enemy.max_hp = enemy.hp = 1000
        step(room, 2, {'attack'})
        self.assertGreaterEqual(enemy.hp, 955)
        self.assertLess(enemy.hp, 1000)

    def test_lethal_melee_hit_prevents_later_enemy_shot_in_same_tick(self):
        room = Room()
        room.player.x, room.player.y, room.player.hp = 5.5, 10.25, 10
        room.enemies[1].active = room.enemies[3].active = False
        ranged = room.enemies[2]
        ranged.x, ranged.y = 5.5, 8.5
        for e in (room.enemies[0], ranged):
            room.start_attack(e)
            e.attack_elapsed = .245
        room.update(set(), 1/60)
        self.assertEqual(room.outcome, 'dead')
        self.assertFalse(room.projectiles)


if __name__ == '__main__':
    unittest.main()
