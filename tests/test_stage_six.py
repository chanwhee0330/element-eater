"""번개 습득과 연쇄 공격, 이어하기 및 전력 장치 검사."""
from math import ceil, floor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import Actor, Room
from src.savegame import SaveStore, restore


class StageSixTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=6)

    def learn_lightning(self):
        room = self.room
        room.sources[-1].phase = 'consumed'
        room.inventory['lightning'] = 1
        room.selected = 'lightning'

    def test_shock_plates_fit_between_static_walls_and_closed_bulkheads(self):
        room = self.room
        walls = [*room.wall_bounds.values(), *room.acquisition['passages']]
        for hazard in room.data['movingHazards']:
            left, top, right, bottom = hazard['bounds']
            with self.subTest(bounds=hazard['bounds']):
                for y in range(floor(top), ceil(bottom)):
                    for x in range(floor(left), ceil(right)):
                        self.assertLess(room.data['tiles'][y][x], room.data['tileIds']['wall'])
                self.assertFalse(any(left < r and l < right and top < b and t < bottom for l, t, r, b in walls))

    def test_lightning_chains_to_three_valid_targets_and_never_consumes(self):
        room = self.room
        self.learn_lightning()
        room.player.x, room.player.y, room.player.facing = 13, 17.5, 'right'
        first = Actor(15, 17.5, 'left', element='water')
        second = Actor(17.5, 17.5, 'left')
        third = Actor(20, 17.5, 'left', element='water')
        fourth = Actor(21, 17.5, 'left', element='water')
        wrong = Actor(14, 17.5, 'left', element='earth')
        room.enemies = [wrong, fourth, third, second, first]
        self.assertTrue(room.skill())
        self.assertTrue(room.start_attack(room.player))
        room.attack_tick(room.player, room.tuning.attack_event)
        self.assertEqual([first.hp, second.hp, third.hp, fourth.hp, wrong.hp],
                         [85, 85, 85, 100, 100])
        self.assertEqual(room.lightning_path, ((13,17.5),(15,17.5),(17.5,17.5),(20,17.5)))
        room.attack_tick(room.player, room.tuning.attack_duration)
        self.assertEqual(room.inventory['lightning'], 1)

    def test_chain_cannot_pass_through_a_wall(self):
        room = self.room
        self.learn_lightning()
        room.player.x, room.player.y, room.player.facing = 14, 8.5, 'right'
        front = Actor(21.5, 8.5, 'left', element='water')
        blocked = Actor(24.6, 8.5, 'left', element='water')
        room.enemies = [front, blocked]
        room.tuning = type(room.tuning)(lightning_range=400)
        self.assertTrue(room.skill())
        self.assertTrue(room.start_attack(room.player))
        room.attack_tick(room.player, room.tuning.attack_event)
        self.assertEqual(front.hp, 85)
        self.assertEqual(blocked.hp, 100)

    def test_save_restores_charged_and_winding_up_attacks(self):
        room = self.room
        self.learn_lightning()
        room.player.x, room.player.y, room.player.facing = 18.6, 21.25, 'up'
        self.assertTrue(room.skill())
        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp) / 'save.json')
            store.write(room)
            restore(store.load(), room)
            self.assertTrue(room.lightning_charged)

            self.assertTrue(room.start_attack(room.player))
            store.write(room)
            restore(store.load(), room)
            self.assertTrue(room.lightning_attack)
            room.attack_tick(room.player, room.tuning.attack_event)
            self.assertGreaterEqual(len(room.lightning_path), 2)
            self.assertEqual(room.inventory['lightning'], 1)

    def test_breaker_opens_orb_then_relay_powers_exit_and_saves(self):
        room = self.room
        source, = room.sources
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(source.phase, 'sealed')
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.update({'connect'}, .01)
        self.assertEqual(source.phase, 'charging')
        self.assertEqual(room.tile(18, 19.75), 3)
        room.player.x, room.player.y = source.x, source.y
        self.assertFalse(room.start_ingest())
        self.assertTrue(all(room.hazard_state(hazard)[0] == 'idle' for hazard in room.data['movingHazards']))
        for _ in range(54):
            room.update(set(), .05)
        self.assertEqual(source.phase, 'orb')
        room.update({'ingest'}, .01)
        for _ in range(8):
            room.update(set(), .05)
        self.assertTrue(room.ingest_consumed)
        self.assertEqual(room.tile(18, 19.75), 3)
        for _ in range(16):
            room.update(set(), .05)
        self.assertEqual(room.selected, 'lightning')
        self.assertEqual(room.tile(18, 19.75), 0)
        for enemy in room.enemies[2:]:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y = room.acquisition['finalSwitch']
        room.update({'connect'}, .01)
        self.assertFalse(room.exit_open)
        room.player.x, room.player.y, room.player.facing = 18.5, 14.45, 'up'
        room.update({'attack'}, .01)
        flash_seen = False
        for _ in range(15):
            room.update(set(), .05)
            flash_seen |= room.acquisition_relay_flash > 0
        self.assertTrue(room.acquisition_relay)
        self.assertTrue(flash_seen)
        self.assertEqual(room.acquisition_power_elapsed, -1)
        room.player.x, room.player.y = room.acquisition['finalSwitch']
        room.update({'connect'}, .01)
        self.assertEqual(room.acquisition_power_elapsed, 0)
        self.assertFalse(room.exit_open)
        for _ in range(24):
            room.update(set(), .05)
        room.update({'connect'}, .01)
        self.assertAlmostEqual(room.acquisition_power_elapsed, 1.21)
        self.assertEqual(room.acquisition_relay_flash, 0)
        self.assertEqual(room.powered_door_lift, 0)
        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp)/'save.json')
            store.write(room)
            restore(store.load(), room)
            self.assertAlmostEqual(room.acquisition_power_elapsed, 1.21)
            for _ in range(27):
                room.update(set(), .05)
            self.assertGreater(room.powered_door_lift, 0)
            self.assertLess(room.powered_door_lift, 1)
            self.assertFalse(room.exit_open)
            for _ in range(10):
                room.update(set(), .05)
            self.assertTrue(room.exit_open)
            store.write(room)
            record = store.load()
            del record['state']['acquisition']['powerElapsed']
            restore(record, room)
        self.assertTrue(room.acquisition_power)
        self.assertTrue(room.exit_open)

    def test_capacitor_formation_resumes_from_save_before_pickup(self):
        room = self.room
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        for _ in range(18):
            room.update(set(), .05)
        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp) / 'save.json')
            store.write(room)
            restore(store.load(), room)
        source, = room.sources
        self.assertEqual(source.phase, 'charging')
        self.assertAlmostEqual(source.age, .9)
        room.player.x, room.player.y = source.x, source.y
        self.assertFalse(room.start_ingest())
        for _ in range(36):
            room.update(set(), .05)
        self.assertTrue(room.start_ingest())

    def test_room_nine_keeps_levels_and_marks_only_wrong_conductors(self):
        room = Room(stage=9)
        room.vine_time = room.vine_gate['burnDuration']
        room.trial_returns = {0, 1}
        room.extinguished = set(range(len(room.fire_barriers)))
        room.plate_pressed = True
        room.gate_time = room.gate_open_seconds
        room.player.x, room.player.y = room.power_puzzle['switch']
        targets = room.power_targets[:]
        room.power_levels[:] = [targets[0], 0, targets[2]]
        room.update({'connect'}, .05)
        self.assertGreater(room.power_flash, 0)
        self.assertEqual(room.power_levels, [targets[0], 0, targets[2]])
        self.assertEqual(room.trial_wrong, {1})
        self.assertEqual(room.power_targets, targets)
        for _ in range(17):
            room.update(set(), .05)
        room.power_levels[:] = targets
        room.update({'connect'}, .05)
        self.assertTrue(room.power_connected)
