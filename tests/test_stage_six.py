"""전력실 퍼즐과 번개 연쇄 공격 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import Actor, Room
from src.savegame import SaveStore, restore


class StageSixTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=6)
        self.room.inventory['lightning'] = 1
        self.room.selected = 'lightning'

    def test_lightning_hits_three_distinct_enemies_of_any_element(self):
        room = self.room
        room.player.x, room.player.y, room.player.facing = 12, 21, 'right'
        earth = Actor(14, 21, 'left', element='earth')
        fire = Actor(17, 21, 'left', element='fire')
        neutral = Actor(20, 21, 'left')
        fourth = Actor(23, 21, 'left', element='lightning')
        behind = Actor(10, 21, 'right', element='water')
        room.enemies = [fourth, behind, neutral, fire, earth]

        room.inventory['water'] = 2
        self.assertTrue(room.skill())
        self.assertTrue(room.lightning_charged)
        self.assertEqual(room.inventory['lightning'], 1)
        self.assertEqual(earth.hp, 100)
        self.assertTrue(room.start_attack(room.player))
        self.assertEqual(room.inventory['lightning'], 1)
        room.attack_tick(room.player, room.tuning.attack_event)
        self.assertTrue(room.lightning_attack)
        self.assertEqual([earth.hp, fire.hp, neutral.hp, fourth.hp, behind.hp], [85, 85, 85, 100, 100])
        self.assertEqual(room.lightning_path, ((12, 21), (14, 21), (17, 21), (20, 21)))
        self.assertEqual(room.inventory['lightning'], 0)
        self.assertEqual(room.selected, 'lightning')
        room.attack_tick(room.player, room.tuning.attack_duration)
        self.assertFalse(room.lightning_attack)
        self.assertEqual(room.selected, 'neutral')
        self.assertEqual(room.inventory['water'], 2)

    def test_lightning_cannot_start_or_chain_through_closed_gate(self):
        room = self.room
        room.player.x, room.player.y, room.player.facing = 17, 13, 'up'
        blocked = Actor(17, 7, 'down', element='lightning')
        room.enemies = [blocked]
        self.assertTrue(room.skill())
        self.assertTrue(room.start_attack(room.player))
        room.attack_tick(room.player, room.tuning.attack_event)
        self.assertTrue(room.lightning_charged)
        self.assertEqual(room.inventory['lightning'], 1)
        self.assertEqual(room.projectiles[0].element, 'lightning')
        room.attack_tick(room.player, room.tuning.attack_duration)
        room.player.attack_cooldown = 0

        front = Actor(17, 10.5, 'down', element='wind')
        room.enemies.append(front)
        room.inventory['lightning'] = 2
        self.assertTrue(room.start_attack(room.player))
        room.attack_tick(room.player, room.tuning.attack_event)
        room.attack_tick(room.player, room.tuning.attack_duration)
        self.assertEqual(front.hp, 85)
        self.assertEqual(blocked.hp, 100)
        self.assertEqual(room.inventory['lightning'], 1)
        self.assertEqual(room.selected, 'lightning')

    def test_save_restores_charged_and_winding_up_attacks(self):
        room = self.room
        room.inventory['water'] = 1
        room.player.x, room.player.y, room.player.facing = 12, 21, 'right'
        enemy = room.enemies[0]
        enemy.x, enemy.y = 14, 21
        self.assertTrue(room.skill())
        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp) / 'save.json')
            store.write(room)
            restored = Room()
            restore(store.load(), restored)
            self.assertTrue(restored.lightning_charged)

            self.assertTrue(restored.start_attack(restored.player))
            store.write(restored)
            restore(store.load(), room)
            self.assertTrue(room.lightning_attack)
            self.assertEqual(room.inventory['lightning'], 1)
            room.attack_tick(room.player, room.tuning.attack_event)
            self.assertEqual(room.inventory['lightning'], 0)

            store.write(room)
            restore(store.load(), restored)
            restored.attack_tick(restored.player, restored.tuning.attack_duration)
            self.assertFalse(restored.lightning_attack)
            self.assertEqual(restored.inventory['lightning'], 0)
            self.assertEqual(restored.selected, 'neutral')
            self.assertEqual(restored.inventory['water'], 1)

    def test_wrong_conductor_levels_reset_then_allow_retry(self):
        room = self.room
        room.power_targets[:] = [3, 2, 1]
        room.power_levels[:] = [3, 1, 1]
        room.player.x, room.player.y = room.power_puzzle['switch']

        room.update({'connect'}, .05)
        self.assertFalse(room.power_gate_open)
        self.assertGreater(room.power_flash, 0)
        self.assertEqual(room.power_levels, [0, 0, 0])
        self.assertEqual(room.power_targets, [3, 2, 1])

        for _ in range(8):
            room.update(set(), .05)
        room.power_levels[:] = room.power_targets
        room.update({'connect'}, .05)
        for _ in range(6):
            room.update(set(), .05)
        self.assertTrue(room.power_gate_open)
