"""렌더러에 의존하지 않는 첫 방 플레이 시나리오 검사."""
import math
import unittest
from src.room import Room, RIM_HALF_X, RIM_HALF_Y


def advance(room, keys=(), seconds=1, fps=120):
    for _ in range(round(seconds * fps)):
        room.update(set(keys), 1 / fps)


class RoomTests(unittest.TestCase):
    def test_entry_then_retreat_keeps_chase(self):
        room = Room()
        start = [(e.x, e.y) for e in room.enemies]
        advance(room, 'w', 2.35)
        self.assertFalse(room.aggro)
        self.assertEqual(start, [(e.x, e.y) for e in room.enemies])
        advance(room, 'w', .2)
        self.assertTrue(room.aggro)
        self.assertTrue(all(e.moving for e in room.enemies if e.kind == 'melee'))
        self.assertEqual(start[2:], [(e.x, e.y) for e in room.enemies if e.kind == 'ranged'])
        advance(room, 's', 1)
        advance(room, seconds=8)
        self.assertTrue(room.aggro)
        self.assertTrue(all(math.hypot(e.x-room.player.x, e.y-room.player.y) < 1
                            for e in room.enemies if e.kind == 'melee'))

    def test_chase_goes_around_wall_without_crossing_hazards(self):
        room = Room()
        room.player.x, room.player.y = 10, 4.5
        for _ in range(30 * 120):
            room.update(set(), 1 / 120)
            self.assertTrue(all(room.tile(e.x, e.y) < 3 for e in room.enemies))
        self.assertTrue(all(math.hypot(e.x-10, e.y-4.5) < 1 for e in room.enemies if e.kind == 'melee'))

    def test_walls_block_but_pits_cause_fall_and_recovery(self):
        room = Room()
        room.player.x, room.player.y = 10, 8.5
        advance(room, 'w')
        self.assertGreaterEqual(room.player.y, 8.2)
        room.reset()
        room.player.y = 14.5
        advance(room, 'a', .4)
        self.assertEqual(room.player.falling, 0)
        # 같은 지형에서 난간이 없는 구간의 낙하를 검사한다.
        room.wall_bounds.pop((9, 14, 'vertical'))
        advance(room, 'a', .4)
        self.assertGreater(room.player.falling, 0)
        advance(room)
        self.assertEqual(room.player.falling, 0)
        self.assertLess(room.tile(room.player.x, room.player.y), 3)

    def test_stone_rims_stop_the_player_before_the_visible_corner(self):
        for stage, right, bottom, y in ((1, 15, 21, 19.5), (2, 21, 28, 26.5)):
            with self.subTest(stage=stage):
                room = Room(stage=stage)
                player = room.player
                player.x, player.y = right - 1.5, y
                room.move(player, 2, 2)
                self.assertLessEqual(player.x, right - RIM_HALF_X - room.radius)
                self.assertLess(player.y, bottom - RIM_HALF_Y)
                self.assertLess(room.tile(player.x, player.y), 3)

                # 이전 버전에서 난간과 겹친 위치로 저장했어도 안쪽으로 돌아갈 수 있다.
                player.x, player.y = right - .24, y
                room.move(player, -.5, 0)
                self.assertAlmostEqual(player.x, right - .74)

    def test_room_three_walls_stop_movement(self):
        room = Room(stage=3)
        room.player.x, room.player.y = 9.1, 20.5
        advance(room, 'a', 1)
        self.assertEqual(room.player.falling, 0)
        self.assertGreaterEqual(room.player.x, 8 + RIM_HALF_X)

    def test_room_three_stops_at_the_spawn_courtyard_right_wall(self):
        room = Room(stage=3)
        room.player.x, room.player.y = 16.2, 26.5
        advance(room, 'd', .5)
        self.assertLess(room.player.x, 18 - RIM_HALF_X)
        self.assertEqual(room.player.falling, 0)

    def test_diagonal_speed_and_frame_rate_independence(self):
        rooms = [Room() for _ in range(3)]
        for room, fps in zip(rooms, (30, 60, 120)):
            advance(room, 'w', .5, fps)
        self.assertAlmostEqual(rooms[0].player.y, rooms[2].player.y)
        room = Room()
        start = room.player.x, room.player.y
        advance(room, 'wd', .25)
        self.assertAlmostEqual(math.hypot(room.player.x-start[0], room.player.y-start[1]), 3.5*.25)

    def test_reset_clears_fall_aggro_and_positions(self):
        room = Room()
        advance(room, 'w', 3)
        self.assertTrue(room.aggro)
        room.reset()
        self.assertFalse(room.aggro)
        self.assertEqual(room.player.y, 19.5)
        self.assertEqual(room.player.facing, 'up')
        self.assertTrue(all(not e.moving and e.falling == 0 for e in room.enemies))

    def test_invalid_time_does_not_move(self):
        room = Room()
        for dt in (0, -1, float('nan'), float('inf')):
            room.update({'w'}, dt)
        self.assertEqual(room.player.y, 19.5)
        self.assertEqual(room.elapsed, 0)

    def test_enemy_can_fall_if_forced_into_pit(self):
        room = Room()
        enemy = room.enemies[0]
        enemy.x, enemy.y = 8, 14
        advance(room, seconds=.1)
        self.assertGreater(enemy.falling, 0)
        advance(room)
        self.assertFalse(enemy.active)

    def test_spikes_are_walkable_and_damage_player(self):
        room = Room()
        room.player.x, room.player.y = 7.5, 17.5
        room.elapsed = 1.5
        advance(room, seconds=.1)
        self.assertFalse(room.spike_contact)
        self.assertEqual(room.player.hp, room.player.max_hp)
        room.elapsed = 2.2
        advance(room, seconds=.1)
        self.assertTrue(room.spike_contact)
        self.assertEqual(room.player.hp, room.player.max_hp - room.tuning.spike_damage)
        advance(room, seconds=.1)
        self.assertEqual(room.player.hp, room.player.max_hp - room.tuning.spike_damage)
        self.assertEqual(room.player.falling, 0)


if __name__ == '__main__':
    unittest.main()
