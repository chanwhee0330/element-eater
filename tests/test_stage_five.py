"""탄환 복도의 두 경로, 흙 지형과 저장 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.combat import Projectile
from src.room import Room
from src.savegame import SaveStore, restore


def advance(room, seconds, keys=''):
    for _ in range(round(seconds * 120)):
        room.update(set(keys), 1 / 120)


class StageFiveTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=5)
        self.room.player.invulnerable = 20

    def place(self, x, y, facing):
        player = self.room.player
        player.x, player.y, player.facing = x / 42, y / 42, facing

    def give_earth(self, count=1):
        self.room.inventory['earth'] = count
        self.room.selected = 'earth'

    def test_central_corridor_reaches_switch_without_bridge(self):
        room = self.room
        self.assertTrue(room.sources[1].hit('wind'))
        advance(room, .55)
        self.place(756, 825, 'up')
        self.assertTrue(room.start_ingest())
        advance(room, .7)
        self.assertEqual(room.selected, 'earth')
        advance(room, 3.94, 'w')
        self.assertGreater(len(room.projectiles), 0)
        advance(room, 1.82, 'd')
        advance(room, .67, 's')
        self.assertTrue(room.turrets_stopped)
        room.projectiles.clear()
        for enemy in room.enemies:
            enemy.active = False
        advance(room, 1)
        self.assertEqual(room.projectiles, [])
        self.assertTrue(room.exit_open)

    def test_right_turret_lane_and_switch_entrance_have_player_clearance(self):
        self.place(812, 402, 'up')
        advance(self.room, .96, 'w')
        self.assertLess(self.room.player.y * 42, 265)
        advance(self.room, 1.44, 'd')
        advance(self.room, .56, 's')
        self.assertTrue(self.room.turrets_stopped)

    def test_side_cover_alcoves_are_enterable_at_the_lower_openings(self):
        for x, y, key, boundary in ((754, 519, 'd', 870), (754, 640, 'a', 635)):
            with self.subTest(y=y):
                self.place(x, y, 'up')
                advance(self.room, .85, key)
                actual = self.room.player.x * 42
                if key == 'd':
                    self.assertGreater(actual, boundary)
                else:
                    self.assertLess(actual, boundary)

    def test_bridge_is_accessible_from_the_south_side_of_the_landing(self):
        self.place(754, 384, 'right')
        advance(self.room, .89, 'd')
        self.give_earth()
        self.assertTrue(self.room.skill())
        advance(self.room, .7, 'd')
        self.assertGreater(self.room.player.x * 42, 975)
        self.assertFalse(self.room.player.falling)

    def test_wall_blocks_projectile_and_failed_cast_does_not_consume(self):
        room = self.room
        self.place(754, 720, 'up')
        self.give_earth(2)
        self.assertTrue(room.skill())
        self.assertFalse(room.skill())
        self.assertEqual(room.inventory['earth'], 1)
        wall, = room.earth_terrain
        self.assertEqual(wall.kind, 'wall')
        _, top, _, _ = wall.bounds
        shot = Projectile(754 / 42, top - .15, 0, 1, 'enemy', 8, 4, 8, element='lightning')
        room.projectiles.append(shot)
        room.update_projectiles(.1)
        self.assertNotIn(shot, room.projectiles)

    def test_bridge_crossing_and_switch_persist_after_reload(self):
        room = self.room
        self.place(884, 366, 'right')
        self.give_earth()
        self.assertTrue(room.skill())
        advance(room, .32, 'd')
        self.assertEqual(room.earth_terrain[0].kind, 'floor')
        self.assertEqual(room.tile(room.player.x, room.player.y, ignore_earth=True), 4)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            room.player.invulnerable = 0
            store.write(room)
            record = store.load()
            self.assertIsNotNone(record)
            restore(record, room)
            advance(room, .62, 'd')
            advance(room, .17, 'w')
            self.assertTrue(room.turrets_stopped)
            self.assertFalse(room.player.falling)
            store.write(room)
            self.assertTrue(store.load()['state']['turret_room']['stopped'])

    def test_expired_bridge_falls_back_to_permanent_ground(self):
        room = self.room
        self.place(884, 366, 'right')
        self.give_earth()
        advance(room, .1)
        self.assertTrue(room.skill())
        advance(room, .32, 'd')
        advance(room, 3.7)
        self.assertGreater(room.player.falling, 0)
        advance(room, .7)
        self.assertEqual(room.player.falling, 0)
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True, ignore_earth=True))
