"""채석교의 낙석·흙 지형·포대와 저장 상태 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.combat import Projectile
from src.room import Room
from src.savegame import SaveStore, restore


def advance(room, seconds, keys=()):
    for _ in range(round(seconds * 120)):
        room.update(set(keys), 1 / 120)


class StageFiveTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=5)

    def give_earth(self):
        room = self.room
        room.sources[-1].phase = 'consumed'
        room.inventory['earth'] = 1
        room.selected = 'earth'

    def test_quarry_orb_is_sealed_until_guards_and_stone_are_cleared(self):
        room = self.room
        source, = room.sources
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.update(set(), .01)
        self.assertEqual(source.phase, 'sealed')
        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x - 1.7, y, 'right'
        room.update({'skill'}, .01)
        advance(room, .9)
        self.assertTrue(room.plate_pressed)
        self.assertEqual(source.phase, 'orb')
        room.player.x, room.player.y = source.x, source.y
        room.update({'ingest'}, .01)
        advance(room, .7)
        self.assertEqual(room.selected, 'earth')

    def test_earth_wall_blocks_projectiles_and_can_be_recast(self):
        room = self.room
        self.give_earth()
        room.player.x, room.player.y, room.player.facing = 12, 18.8, 'up'
        self.assertTrue(room.skill())
        self.assertFalse(room.skill())
        self.assertEqual(room.inventory['earth'], 1)
        _, top, _, _ = room.earth_terrain[0].bounds
        shot = Projectile(12, top - .15, 0, 1, 'enemy', 8, 4, 8, element='lightning')
        room.projectiles.append(shot)
        room.update_projectiles(.1)
        self.assertNotIn(shot, room.projectiles)
        advance(room, 4.1)
        self.assertTrue(room.skill())

    def test_bridge_is_walkable_from_both_banks_and_persists_with_switch(self):
        room = self.room
        self.give_earth()
        room.player.x, room.player.y, room.player.facing = 15.6, 15.45, 'right'
        self.assertTrue(room.skill())
        advance(room, .45, 'd')
        self.assertEqual(room.tile(room.player.x, room.player.y, ignore_earth=True), 4)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restore(store.load(), room)
            advance(room, 1.35, 'd')
            self.assertGreater(room.player.x, 21)
            self.assertFalse(room.player.falling)
            advance(room, 4.1)
            room.player.x, room.player.y, room.player.facing = 21.6, 15.45, 'left'
            self.assertTrue(room.skill())
            room.player.x, room.player.y = room.turret_room['switch']
            room.update(set(), .01)
            self.assertTrue(room.turrets_stopped)
            store.write(room)
            restore(store.load(), room)
        self.assertTrue(room.turrets_stopped)
        self.assertEqual(room.tile(18, 15.45, ignore_earth=True), 0)

    def test_expired_bridge_falls_back_to_permanent_ground(self):
        room = self.room
        self.give_earth()
        room.player.x, room.player.y, room.player.facing = 15.6, 15.45, 'right'
        advance(room, .1)
        self.assertTrue(room.skill())
        advance(room, .7, 'd')
        advance(room, 3.5)
        self.assertGreater(room.player.falling, 0)
        advance(room, .7)
        self.assertEqual(room.player.falling, 0)
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True, ignore_earth=True))
