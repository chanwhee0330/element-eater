"""삼중 성문의 평형추·레이저·저장 회귀 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import Projectile, Room
from src.savegame import SaveStore, restore


class TrialRoomTests(unittest.TestCase):
    def test_six_push_solution_and_west_sluice(self):
        room = Room(stage=9)
        self.assertEqual(room.tile(7.25, 17.8), 3)
        _, _, fixed_row, _ = room.active_lasers.beams(())[0]
        for _ in range(16):
            room.update(set(), .05)
        _, _, swept_row, _ = room.active_lasers.beams(())[0]
        self.assertGreater(swept_row, fixed_row + .8)
        self.assertTrue(room.active_lasers.touches_beam(32.5, swept_row, room.radius, ()))
        self.assertFalse(room.active_lasers.touches_beam(32.5, fixed_row, room.radius, ()))
        room.selected = 'wind'
        for facing, stance, destination in (
            ('up', (27.5, 25.5), (27.5, 21.5)),
            ('right', (26.5, 21.5), (29.5, 21.5)),
            ('down', (29.5, 20.5), (29.5, 23.5)),
            ('right', (28.5, 23.5), (30.5, 23.5)),
            ('up', (30.5, 24.5), (30.5, 22.5)),
            ('right', (29.5, 22.5), (31.5, 22.5)),
        ):
            self.assertTrue(room.fits(*stance, safe=True))
            room.player.x, room.player.y = stance
            room.player.facing = facing
            room.skill()
            for _ in range(18):
                room.update_puzzle(.05)
            self.assertEqual(room.block, destination)
        self.assertTrue(room.plate_pressed)
        for _ in range(22):
            room.update(set(), .05)
        self.assertAlmostEqual(room.gate_time / room.gate_open_seconds, .5)
        self.assertEqual(room.tile(7.25, 17.8), 3)
        self.assertEqual(room.trial_flow(0), 0)
        with TemporaryDirectory() as tmp:
            store = SaveStore(Path(tmp) / 'continue.json')
            store.write(room)
            restored = Room(stage=9)
            restore(store.load(), restored)
        self.assertEqual(restored.gate_time, room.gate_time)
        room = restored
        for _ in range(23):
            room.update(set(), .05)
        self.assertEqual(room.tile(7.25, 17.8), 0)
        room.player.x, room.player.y = 7.25, 16.9
        for element in ('water', 'fire'):
            room.projectiles.append(Projectile(7.25, 16.9, 0, -1, 'hero', 10, 4, 5, element=element))
            for _ in range(24):
                room.update(set(), .05)
        self.assertEqual(room.extinguished, {0})
        self.assertTrue(room.vine_open)
        room.player.x, room.player.y = room.trial['switches'][0]
        room.update({'connect'}, .05)
        self.assertEqual(room.trial_returns, {0})
        self.assertFalse(room.trial_laser_locked)
        self.assertEqual(room.trial_wheel_time, 0)
        self.assertEqual(room.tile(33, 14.3), 3)
        self.assertFalse(room.conductor_powered(0))
        for _ in range(37):
            room.update(set(), .05)
        self.assertTrue(room.trial_laser_locked)
        self.assertGreater(room.trial_wheel_time, 0)
        self.assertLess(room.trial_wheel_time, room.trial_wheel_reveal_seconds)
        self.assertEqual(room.tile(33, 14.3), 0)
        self.assertEqual(room.active_lasers.beams(())[0][2], fixed_row)

    def test_wheel_door_blocks_the_corridor_until_the_arch_opens(self):
        room = Room(stage=9)
        left, top, right, bottom = room.trial['wheelGate']
        middle = (top + bottom) / 2
        self.assertTrue(all(room.tile(x/10, middle) == 3 for x in range(310, 350)))
        self.assertIn((left, top, right, bottom), room.trial_obstacles())
        room.player.x, room.player.y = 33, 20.3
        for _ in range(10):
            room.update({'w'}, .05)
        self.assertGreater(room.player.y, bottom)

        room.trial_returns = {0}
        for _ in range(5):
            room.update({'w'}, .05)
        self.assertFalse(room.trial_wheel_open)
        self.assertGreater(room.player.y, bottom)
        for _ in range(12):
            room.update({'w'}, .05)
        self.assertTrue(room.trial_wheel_open)
        self.assertLess(room.player.y, top)
        self.assertTrue(room.fits(33, middle, safe=True))
        self.assertFalse(room.fits(31.5, middle, safe=True))
        self.assertFalse(room.fits(34.5, middle, safe=True))
        self.assertNotIn((left, top, right, bottom), room.trial_obstacles())
        for _ in range(10):
            room.update({'s'}, .05)
        self.assertGreater(room.player.y, bottom)

    def test_older_save_behind_closed_wheel_door_resumes_on_approach(self):
        room = Room(stage=9)
        for y in (18.4, 19.4):
            room.player.x, room.player.y = 32.25, y
            room.safe = 32.25, y, 'up'
            with TemporaryDirectory() as tmp:
                store = SaveStore(Path(tmp) / 'continue.json')
                store.write(room)
                restored = Room(stage=9)
                restore(store.load(), restored)
            point = restored.player.x, restored.player.y
            self.assertGreater(point[1], room.trial['wheelGate'][3])
            self.assertTrue(restored.fits(*point, safe=True))
            self.assertEqual(restored.safe[:2], point)
            self.assertFalse(restored.trial_wheel_open)

    def test_earth_cuts_the_laser_and_the_east_lever_sends_west_power(self):
        room = Room(stage=9)
        room.block = tuple(room.puzzle['plate'])
        room.plate_pressed = True
        room.gate_time = room.gate_open_seconds
        room.extinguished = {0}
        room.vine_time = room.vine_gate['burnDuration']
        room.trial_returns = {0}
        west_x, west_y = room.power_puzzle['conductors'][0]
        room.projectiles.append(Projectile(west_x, west_y+.6, 0, -1, 'hero', 10, 4, 5,
                                           element='lightning'))
        room.update(set(), .05)
        self.assertEqual(room.power_levels[0], 0)
        room.player.x, room.player.y = 31.5, 17.2
        room.move(room.player, 0, -1.3)
        self.assertGreater(room.player.y, 16.55)
        room.player.x, room.player.y = 33.1, 18.2
        room.player.facing = 'up'
        room.selected = 'earth'
        self.assertFalse(room.fits(31.5, 16.55, safe=True))
        self.assertEqual(room.tile(25.5, 12.5), 3)
        self.assertTrue(room.cast_earth())
        self.assertTrue(room.fits(31.5, 16.55, safe=True))
        self.assertFalse(room.fits(34.5, 16.55, safe=True))
        self.assertEqual(room.tile(25.5, 12.5), 3)
        room.player.x, room.player.y = 31.5, 17.2
        room.move(room.player, 0, -1.3)
        self.assertLess(room.player.y, 16.55)
        wall, = room.earth_terrain
        room.earth_terrain.clear()
        self.assertFalse(room.fits(31.5, 16.55, safe=True))
        room.earth_terrain.append(wall)
        room.player.x, room.player.y = room.trial['switches'][1]
        self.assertFalse(room.fits(25.5, 12.5, safe=True))
        room.update({'connect'}, .05)
        room.earth_terrain.clear()
        self.assertTrue(all(room.fits(x / 4, 12.5, safe=True) for x in range(90, 115)))
        self.assertTrue(room.fits(31.5, 16.55, safe=True))
        self.assertTrue(room.fits(34.5, 16.55, safe=True))
        self.assertFalse(room.conductor_powered(0))
        for _ in range(28):
            room.update(set(), .05)
        self.assertTrue(room.conductor_powered(0))
        for _ in range(3):
            room.projectiles.append(Projectile(west_x, west_y+.6, 0, -1, 'hero', 10, 4, 5,
                                               element='lightning'))
            room.update(set(), .05)
        self.assertEqual(room.power_levels[0], 3)
        room.player.x, room.player.y = room.power_puzzle['switch']
        room.safe = room.player.x, room.player.y, 'up'
        room.power_levels[1:] = room.power_targets[1:]
        room.update({'connect'}, .05)
        self.assertTrue(room.power_connected)
        with TemporaryDirectory() as tmp:
            store = SaveStore(Path(tmp) / 'continue.json')
            store.write(room)
            restored = Room(stage=9)
            restore(store.load(), restored)
        self.assertEqual(restored.trial_returns, {0, 1})
        self.assertTrue(restored.conductor_powered(0))
        self.assertIsNone(restored.active_lasers)
        self.assertEqual(restored.power_levels, [3, 1, 2])
        self.assertTrue(restored.power_connected)

    def test_paths_reuse_collision_samples_and_follow_the_open_power_gate(self):
        room = Room(stage=9)
        room.preload_reference_paths()
        room.player.x, room.player.y = 19.5, 9.5
        first = room.reference_distances()
        self.assertNotIn((39, 14), first)
        _, links, samples = room.reference_path_cache
        room.player.y = 9
        room.reference_distances()
        self.assertIs(room.reference_path_cache[1], links)
        self.assertIs(room.reference_path_cache[2], samples)
        room.power_connected = True
        room.power_gate_time = room.gate_open_seconds
        self.assertIn((39, 14), room.reference_distances())

    def test_sweeping_laser_recovers_to_a_position_outside_its_path(self):
        room = Room(stage=9)
        room.player.x, room.player.y = 32.5, 18.3
        room.update(set(), .05)
        safe = room.safe
        room.player.y = 17.55
        for _ in range(18):
            room.update(set(), .05)
        self.assertEqual((room.player.x, room.player.y), safe[:2])
        self.assertEqual(sum(effect.text == '레이저 복구' for effect in room.feedback), 1)
