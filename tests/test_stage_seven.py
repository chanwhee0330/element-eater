from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import EarthTerrain, Room
from src.savegame import SaveStore, restore


class StageSevenTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=7)

    def tick(self, seconds, keys=()):
        for _ in range(round(seconds*60)):
            self.room.update(set(keys), 1/60)

    def shoot(self, element, x, y, facing='up'):
        room = self.room
        room.selected = element
        room.player.x, room.player.y, room.player.facing = x, y, facing
        self.tick(1, {'attack'})
        self.tick(.7)

    def reachable(self, start=(18, 18)):
        # Half-tile samples are finer than the shortest gate depth.
        origin = tuple(round(v*2) for v in start)
        queue = deque([origin])
        seen = {origin}
        while queue:
            x, y = queue.popleft()
            for nxt in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if nxt not in seen and self.room.fits(nxt[0]/2, nxt[1]/2, safe=True):
                    seen.add(nxt)
                    queue.append(nxt)
        return seen

    def test_learned_elements_and_each_gate(self):
        room = self.room
        self.assertEqual(len(room.inventory), 5)
        self.assertTrue(all(room.inventory.values()))
        self.assertFalse(room.sources)
        self.assertNotIn((36, 36), self.reachable((18,22.5)))
        self.shoot('water', 18, 22.75)
        self.assertEqual(room.extinguished, {0})
        self.assertIn((36, 36), self.reachable((18,22.5)))

        # East can be solved first, but neither it nor its shortcut can bypass the gate.
        self.assertIn((58, 17), self.reachable())
        self.shoot('lightning', 28.5, 8.45, 'right')
        self.assertTrue(room.sluice_pump)
        self.assertFalse(room.sluice_open)
        self.assertNotIn((36, 12), self.reachable())
        self.assertNotIn((17, 17), self.reachable())
        self.shoot('fire', 8, 14.75)
        self.assertTrue(room.vine_open)
        self.assertIn((17, 17), self.reachable())
        room.player.x, room.player.y = 8.7, 9.05
        self.tick(.25, {'connect'})
        self.assertTrue(room.sluice_wheel)
        self.assertFalse(room.sluice_open)
        self.assertNotIn((36, 12), self.reachable())

        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp)/'continue.json')
            store.write(room)
            restored = Room(stage=7)
            restore(store.load(), restored)
        self.assertAlmostEqual(restored.garden_gate_time, room.garden_gate_time)
        self.assertFalse(restored.sluice_open)
        self.room = restored
        self.tick(.8)
        self.assertTrue(restored.sluice_open)
        self.assertIn((36, 12), self.reachable())
        self.assertTrue(all(restored.tile(*point) == 0 for point in ((13.6,8.5), (22.4,8.5), (18,10.5))))
        self.assertFalse(restored.exit_open)
        for enemy in restored.enemies:
            restored.damage(enemy, enemy.max_hp)
        restored.player.x, restored.player.y = 18, 1.85
        self.tick(.1)
        self.assertIsNone(restored.outcome)
        self.tick(.5)
        self.assertEqual(restored.outcome, 'clear')

    def test_west_first_keeps_north_and_both_bridges_closed(self):
        self.room.extinguished.add(0)
        self.room.vine_time = self.room.vine_gate['burnDuration']
        self.room.player.x, self.room.player.y = 8.7, 9.05
        self.tick(1, {'connect'})
        self.assertTrue(self.room.sluice_wheel)
        self.assertFalse(self.room.sluice_ready)
        self.assertNotIn((36, 12), self.reachable())
        self.assertTrue(all(self.room.tile(*point) == 3 for point in ((13.6,8.5), (22.4,8.5), (18,10.5))))

    def test_paths_reuse_links_and_recheck_a_changed_obstacle(self):
        room = self.room
        room.extinguished.add(0)
        room.player.x, room.player.y = 18, 20
        room.preload_reference_paths()
        self.assertIn((36, 38), room.reference_distances())
        links = room.reference_path_cache[1]
        unchanged = links[(36, 34)]
        room.player.x = 18.5
        room.reference_distances()
        self.assertIs(links[(36, 34)], unchanged)

        room.earth_terrain.append(EarthTerrain('wall', (17.7, 19.1, 18.3, 19.18), 1))
        room.reference_distances()
        self.assertNotIn((36, 38), links[(36, 39)])
        self.assertIs(links[(36, 34)], unchanged)
        room.earth_terrain.clear()
        room.reference_distances()
        self.assertIn((36, 38), links[(36, 39)])
