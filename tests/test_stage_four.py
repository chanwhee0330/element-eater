"""3번 방 추격과 4번 방 퍼즐·바람 전투 검증."""
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import Room
from src.savegame import SaveStore, restore


def advance(room, seconds):
    for _ in range(round(seconds * 120)):
        room.update(set(), 1 / 120)


class StageFourTests(unittest.TestCase):
    def test_stage_three_melee_follows_the_offset_corridor_after_the_vines_open(self):
        room = Room(stage=3)
        room.vine_time = room.vine_gate['burnDuration']
        room.player.x, room.player.y = 24, 9.5
        room.player.invulnerable = 12
        lower_melee, _, upper_melee, _ = room.enemies
        advance(room, 9)
        for enemy in (lower_melee, upper_melee):
            self.assertLess(math.hypot(enemy.x - 24, enemy.y - 9.5), 1.1)

    def test_wind_source_ingestion_push_plate_save_and_exit(self):
        room = Room(stage=4)
        first, second = room.sources
        self.assertTrue(first.hit('fire'))
        for _ in range(3):
            self.assertTrue(second.hit('neutral'))
        advance(room, .55)
        for source in (first, second):
            room.player.x, room.player.y = source.x + .85, source.y
            self.assertTrue(room.start_ingest())
            advance(room, .7)
        self.assertEqual(room.inventory['wind'], 2)
        self.assertEqual(room.selected, 'wind')

        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x - 2, y, 'right'
        gate = room.puzzle['gate']
        gate_x, gate_y = (gate[0] + gate[2]) / 2, (gate[1] + gate[3]) / 2
        self.assertEqual(room.tile(gate_x, gate_y), 3)
        self.assertTrue(room.skill())
        advance(room, .25)
        self.assertGreater(room.block[0], x + 1)
        self.assertFalse(room.plate_pressed)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = store.load()
            self.assertIsNotNone(record)
            room = Room()
            restore(record, room)
            self.assertEqual(room.block_direction, 'right')
            advance(room, 1)
            self.assertTrue(room.plate_pressed)
            self.assertEqual(room.block, tuple(room.puzzle['plate']))
            self.assertEqual(room.tile(gate_x, gate_y), 0)
            self.assertEqual(room.inventory['wind'], 1)
            store.write(room)
            self.assertTrue(store.load()['state']['stone_puzzle']['pressed'])

        self.assertFalse(room.exit_open)
        room.player.x, room.player.y = room.data['plannedExit'].values()
        room.player.facing = 'right'
        enemy = room.enemies[0]
        enemy.x, enemy.y = room.player.x + 2, room.player.y
        for other in room.enemies[1:]:
            other.active = False
        for _ in range(2):
            self.assertTrue(room.start_attack(room.player))
            advance(room, .8)
        self.assertEqual(room.inventory['wind'], 1)
        self.assertEqual(room.outcome, 'clear')

    def test_block_slides_in_all_directions_and_stops_at_walls(self):
        for facing in ('up', 'down', 'left', 'right'):
            with self.subTest(facing=facing):
                room = Room(stage=4)
                x, y = room.block
                dx, dy = room.direction(facing)
                room.player.x, room.player.y = x - dx, y - dy
                room.player.facing = facing
                room.inventory['wind'] = 1
                room.selected = 'wind'
                self.assertTrue(room.skill())
                advance(room, 3)
                self.assertGreater((room.block[0] - x) * dx + (room.block[1] - y) * dy, 1)
                self.assertIsNone(room.block_direction)
                if facing != 'right':
                    self.assertFalse(room.plate_pressed)
                    self.assertEqual(room.tile(room.block[0] + dx * .57, room.block[1] + dy * .57,
                                               ignore_block=True), 3)

    def test_wind_enemy_push_stops_after_a_short_distance_on_open_ground(self):
        room = Room(stage=4)
        enemy = room.enemies[-1]
        room.player.x, room.player.y, room.player.facing = 18, 6, 'right'
        enemy.x, enemy.y = 19, 6
        room.inventory['wind'] = 1
        room.selected = 'wind'
        self.assertTrue(room.skill())
        advance(room, 1)
        self.assertAlmostEqual(enemy.x, 23.8)
        self.assertFalse(enemy.wind_sliding)

    def test_wind_pushes_earth_enemy_to_a_cliff_without_direct_damage(self):
        room = Room(stage=4)
        enemy = room.enemies[1]
        room.player.x, room.player.y, room.player.facing = 24, 9.2, 'right'
        enemy.x, enemy.y = 25.5, 9.2
        room.inventory['wind'] = 1
        room.selected = 'wind'
        self.assertTrue(room.skill())
        advance(room, 1.5)
        self.assertFalse(enemy.active)
        self.assertEqual(enemy.hp, enemy.max_hp)


if __name__ == '__main__':
    unittest.main()
