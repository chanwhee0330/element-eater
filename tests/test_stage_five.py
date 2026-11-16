"""채석교의 낙석·흙 지형·포대와 저장 상태 검사."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
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
        pushes = (
            ((6.5, 27.5), 'right', (8.5, 27.5)),
            ((8.5, 28.5), 'up', (8.5, 25.5)),
            ((7.5, 25.5), 'right', (11.5, 25.5)),
            ((11.5, 24.5), 'down', (11.5, 27.5)),
            ((10.5, 27.5), 'right', (14.5, 27.5)),
            ((14.5, 28.5), 'up', (14.5, 25.5)),
        )
        for index, (stand, facing, target) in enumerate(pushes):
            room.player.x, room.player.y = stand
            room.player.facing = facing
            room.update({'skill'}, .01)
            advance(room, .6)
            self.assertEqual(room.block, target)
            self.assertEqual(source.phase, 'orb' if index == len(pushes) - 1 else 'sealed')
        self.assertTrue(room.plate_pressed)
        self.assertEqual(source.phase, 'orb')
        room.player.x, room.player.y = source.x, source.y
        room.update({'ingest'}, .01)
        advance(room, .7)
        self.assertEqual(room.selected, 'earth')

    def test_old_quarry_save_keeps_cleared_puzzle_and_moves_hero_out_of_new_wall(self):
        room = self.room
        self.give_earth()
        room.plate_pressed = True
        room.gate_time = room.gate_open_seconds
        room.turrets_stopped = True
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
        state = record['state']
        state['map_revision'] = 5
        state['player'].update(x=13.5, y=25.5, hp=75)
        state['safe'] = [13.5, 25.5, 'right']
        state['stone_puzzle']['block'] = [13.75, 25.5]
        restore(record, room)
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True))
        self.assertEqual(room.player.hp, 75)
        self.assertEqual(room.block, tuple(room.puzzle['plate']))
        self.assertTrue(room.plate_pressed)
        self.assertEqual(room.selected, 'earth')
        self.assertTrue(room.turrets_stopped)

    def test_previous_quarry_layout_relocates_actors_on_removed_ground(self):
        room = self.room
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
        state = record['state']
        state['map_revision'] = 6
        state['stone_puzzle'].update(block=[8.2, 27.5], direction='right')
        state['enemies'][-1].update(x=25, y=19.2, hp=21)
        restore(record, room)
        self.assertEqual(room.block, (8.2, 27.5))
        self.assertEqual(room.block_direction, 'right')
        enemy = room.enemies[-1]
        self.assertTrue(room.fits(enemy.x, enemy.y, safe=True))
        self.assertEqual(enemy.hp, 21)

        state['sources'][0]['phase'] = 'consumed'
        state['inventory']['earth'] = 1
        state['selected'] = 'earth'
        state['player'].update(x=23.5, y=22.5, hp=75)
        state['safe'] = [23.5, 22.5, 'up']
        state['stone_puzzle'].update(block=room.puzzle['plate'], direction=None, pressed=True)
        state['turret_room']['stopped'] = True
        restore(record, room)
        self.assertGreater(room.player.x, room.earth_bridge[2])
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True))
        self.assertEqual(room.safe[:2], (room.player.x, room.player.y))
        self.assertEqual(room.player.hp, 75)
        self.assertTrue(room.turrets_stopped)

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

    def test_entrance_turrets_cross_the_gap_and_hit_the_far_wall(self):
        room = self.room
        room.update(set(), .01)
        first, = room.projectiles
        advance(room, .87)
        second = room.projectiles[1]
        self.assertIs(room.projectiles[0], first)
        self.assertLess(first.x, room.earth_bridge[2])
        self.assertEqual(room.tile(first.x, first.y), 4)
        advance(room, 2.3)
        for shot, (wall_x, wall_y) in zip((first, second), room.turret_room['shotTargets']):
            with self.subTest(y=wall_y):
                self.assertFalse(shot.active)
                self.assertGreater(shot.remaining, 0)
                left, top, right, bottom = room.wall_bounds[wall_x, int(wall_y), 'vertical']
                self.assertTrue(left <= shot.x < right and top <= shot.y < bottom)

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
            self.assertFalse(room.turrets_stopped)
            advance(room, 4.1)
            room.player.x, room.player.y, room.player.facing = 21.6, 15.45, 'left'
            self.assertTrue(room.skill())
            advance(room, .88, 'a')
            advance(room, 1.18, 'w')
            self.assertTrue(room.can_stop_turrets)
            self.assertFalse(room.turrets_stopped)
            advance(room, 4.1)
            self.assertIsNone(room.turret_bridge_floor)
            self.assertFalse(room.player.falling)
            room.update({'connect'}, .01)
            self.assertTrue(room.turrets_stopped)
            self.assertIsNone(room.turret_bridge_floor)
            store.write(room)
            restore(store.load(), room)
        self.assertTrue(room.turrets_stopped)
        self.assertEqual(room.tile(18, 15.45, ignore_earth=True), 0)
        advance(room, 4.2)
        self.assertFalse(room.player.falling)

    def test_turret_switch_cannot_be_used_from_the_middle_of_the_bridge(self):
        room = self.room
        self.give_earth()
        room.player.x, room.player.y, room.player.facing = 15.6, 15.45, 'right'
        self.assertTrue(room.skill())
        advance(room, .8, 'd')
        room.update({'connect'}, .01)
        self.assertFalse(room.turrets_stopped)
        self.assertFalse(room.can_stop_turrets)

    def test_expired_bridge_falls_back_to_permanent_ground(self):
        room = self.room
        self.give_earth()
        room.player.x, room.player.y, room.player.facing = 15.6, 15.45, 'right'
        advance(room, .1)
        self.assertTrue(room.skill())
        advance(room, .8, 'd')
        self.assertFalse(room.can_stop_turrets)
        advance(room, 3.5)
        self.assertGreater(room.player.falling, 0)
        advance(room, .7)
        self.assertEqual(room.player.falling, 0)
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True, ignore_earth=True))
