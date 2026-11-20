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
        for _ in range(7):
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

    def test_earth_cuts_the_laser_and_the_lever_opens_the_return_gate(self):
        room = Room(stage=9)
        room.block = tuple(room.puzzle['plate'])
        room.plate_pressed = True
        room.gate_time = room.gate_open_seconds
        room.extinguished = {0}
        room.vine_time = room.vine_gate['burnDuration']
        room.trial_returns = {0}
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
        room.player.x, room.player.y = room.power_puzzle['switch']
        room.safe = room.player.x, room.player.y, 'up'
        room.power_levels[:] = room.power_targets
        room.update({'connect'}, .05)
        self.assertTrue(room.power_connected)
        with TemporaryDirectory() as tmp:
            store = SaveStore(Path(tmp) / 'continue.json')
            store.write(room)
            restored = Room(stage=9)
            restore(store.load(), restored)
        self.assertEqual(restored.trial_returns, {0, 1})
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
