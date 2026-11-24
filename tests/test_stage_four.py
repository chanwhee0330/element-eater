"""화로와 풍차의 습득·화상·석교 동작 검사."""
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


class StageFourTests(unittest.TestCase):
    def test_fire_requires_extinguishing_the_furnace_entry_and_beating_guards(self):
        room = Room(stage=3)
        orb, = room.sources
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(orb.phase, 'sealed')

        room.player.x, room.player.y, room.player.facing = 15.6, 15.75, 'right'
        self.assertTrue(room.start_attack(room.player))
        advance(room, .8)
        self.assertEqual(room.extinguished, {0})
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(orb.phase, 'igniting')
        self.assertFalse(room.start_ingest())
        advance(room, 1.1)
        self.assertEqual(orb.phase, 'orb')

    def test_forge_route_turns_next_to_the_blocked_vines(self):
        room = Room(stage=3)
        room.player.hp = 100
        advance(room, 1.7, 'w')
        advance(room, 1.3, 'd')
        self.assertLess(room.player.x, 18)
        room.player.x = 15.35
        advance(room, 2, 'w')
        vine_bottom = room.conductor_vine['y'] + room.conductor_vine['height']
        self.assertGreater(room.player.y, vine_bottom)
        self.assertLess(room.player.y - vine_bottom, .4)
        advance(room, 2, 'd')
        self.assertLess(room.player.x, 18.15)
        room.extinguished.add(0)
        advance(room, 1.35, 'd')
        self.assertGreater(room.player.x, 21)

    def test_fire_ignition_resumes_after_saving_mid_animation(self):
        room = Room(stage=3)
        room.extinguished.add(0)
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        advance(room, .35)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restore(store.load(), room)
        self.assertEqual(room.sources[0].phase, 'igniting')
        self.assertAlmostEqual(room.sources[0].age, .35)
        advance(room, .73)
        self.assertEqual(room.sources[0].phase, 'orb')

    def test_old_forge_save_keeps_learned_fire_and_solved_conditions(self):
        room = Room(stage=3)
        room.extinguished.add(0)
        room.sources[0].phase = 'consumed'
        room.inventory['fire'], room.selected = 1, 'fire'
        room.player.x, room.player.y, room.player.hp = 18.5, 20.5, 67
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
            record['state']['map_revision'] = 5
            restore(record, room)
        self.assertEqual(room.player.hp, 67)
        self.assertTrue(room.fits(room.player.x,room.player.y,safe=True))
        self.assertEqual(room.selected, 'fire')
        self.assertEqual(room.extinguished, {0})

    def test_fire_burn_only_applies_to_the_weak_element(self):
        room = Room(stage=3)
        for enemy in room.enemies:
            damage = room.tuning.elemental_damage
            room.projectiles.append(Projectile(enemy.x, enemy.y + .25, 0, -1, 'hero',
                                               8, 1, damage, element='fire'))
            room.update_projectiles(.01)
            self.assertEqual(enemy.burn_ticks, 3 if enemy.element == 'wind' else 0)
        wind = room.enemies[-1]
        hp = wind.hp
        advance(room, .67)
        self.assertEqual(wind.hp, hp - 3)

    def test_windmill_base_blocks_walking_from_all_sides(self):
        room = Room(stage=4)
        for enemy in room.enemies:
            room.damage(enemy, enemy.hp)
        left, top, right, bottom = room.windmill['base']
        x, y = (left + right) / 2, (top + bottom) / 2
        radius = room.radius
        approaches = (
            ('d', left - .8, y, left - radius, y),
            ('a', right + .8, y, right + radius, y),
            ('s', x, top - 1, x, top - radius),
            ('w', x, bottom + 1, x, bottom + radius),
        )
        for key, start_x, start_y, stop_x, stop_y in approaches:
            with self.subTest(key=key):
                room.player.x, room.player.y = start_x, start_y
                advance(room, .7, (key,))
                self.assertAlmostEqual(room.player.x, stop_x, delta=.04)
                self.assertAlmostEqual(room.player.y, stop_y, delta=.04)
                self.assertTrue(room.fits(room.player.x, room.player.y, safe=True))

        switch_x, switch_y = room.acquisition['switch']
        room.player.x, room.player.y = switch_x, top - .7
        advance(room, (switch_y - room.player.y) / room.data['preview']['playerSpeed'], 's')
        self.assertAlmostEqual(room.player.y, switch_y, delta=.04)
        room.update({'connect'}, .01)
        self.assertEqual(room.sources[0].phase, 'gathering')
        advance(room, .5, 'a')
        advance(room, room.windmill['releaseSeconds'])
        self.assertTrue(room.start_ingest())

    def test_save_inside_windmill_base_resumes_at_the_front(self):
        room = Room(stage=4)
        for enemy in room.enemies:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        advance(room, .8)
        room.player.x, room.player.y = room.windmill['origin']
        room.player.hp = 76
        room.safe = (room.player.x, room.player.y, 'up')
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restore(store.load(), room)
        self.assertEqual((room.player.x, room.player.y), tuple(room.acquisition['orb']))
        self.assertEqual(room.player.hp, 76)
        self.assertTrue(room.fits(*room.safe[:2], safe=True))
        self.assertEqual(room.remaining_enemies, 0)
        self.assertEqual(room.sources[0].phase, 'gathering')
        self.assertAlmostEqual(room.sources[0].age, .8)

    def test_wind_switch_requires_all_enemies_then_slides_plate_and_restores_moving_block(self):
        room = Room(stage=4)
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.player.x, room.player.y, room.player.facing = 10.2, 19.65, 'up'
        room.update({'attack'}, .01)
        advance(room, 1.4)
        self.assertTrue(room.vine_open)
        source, = room.sources
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(source.phase, 'sealed')
        last_enemy = room.enemies[-1]
        self.assertEqual(last_enemy.element, 'neutral')
        self.assertGreater(last_enemy.y, room.acquisition['bridge'][3])
        room.damage(last_enemy, last_enemy.hp)
        advance(room, .2)
        self.assertEqual(source.phase, 'sealed')
        room.player.x -= 2.5
        room.update({'connect'}, .01)
        self.assertEqual(source.phase, 'sealed')
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(source.phase, 'gathering')
        self.assertFalse(room.start_ingest())
        advance(room, room.windmill['releaseSeconds'] + .02)
        self.assertEqual(source.phase, 'orb')
        room.player.x = source.x
        room.player.y = source.y
        room.update({'ingest'}, .01)
        advance(room, .7)
        self.assertEqual(room.selected, 'wind')

        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x - 1, y, 'right'
        self.assertEqual(room.tile(18, 15), 4)
        room.update({'skill'}, .01)
        advance(room, .12)
        self.assertGreater(room.block[0], x)
        self.assertFalse(room.plate_pressed)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restore(store.load(), room)
        self.assertEqual(room.block_direction, 'right')
        advance(room, .7)
        self.assertEqual(room.block, (15.5, 21.5))
        self.assertIsNone(room.block_direction)
        self.assertFalse(room.plate_pressed)
        for stand, facing, stop in (
            ((15.5, 20.25), 'down', (15.5, 23.5)),
            ((17.25, 23.5), 'left', (13.5, 23.5)),
            ((13.5, 25), 'up', (13.5, 18.5)),
        ):
            room.player.x, room.player.y = stand
            room.player.facing = facing
            room.update({'skill'}, .01)
            advance(room, .85)
            self.assertEqual(room.block, stop)
            self.assertFalse(room.plate_pressed)
        room.player.x, room.player.y, room.player.facing = 11.5, 18.5, 'right'
        room.update({'skill'}, .01)
        advance(room, 1.2)
        self.assertEqual(room.block, tuple(room.puzzle['plate']))
        self.assertEqual(room.tile(18, 15), 0)
        self.assertEqual(room.inventory['wind'], 1)
        room.player.x, room.player.y = 17.5, 17.7
        advance(room, 1.7, 'w')
        self.assertLess(room.player.y, 13)
        self.assertFalse(room.player.falling)

    def test_wind_orb_gathering_is_saved_and_ends_at_pickup_point(self):
        room = Room(stage=4)
        room.vine_time = room.vine_gate['burnDuration']
        for enemy in room.enemies:
            room.damage(enemy, enemy.hp)
        orb, = room.sources
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        room.player.x, room.player.y = orb.x, orb.y + .8
        advance(room, 1.35)
        self.assertEqual(orb.phase, 'gathering')
        self.assertFalse(room.start_ingest())
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restore(store.load(), room)
        self.assertEqual(room.sources[0].phase, 'gathering')
        self.assertAlmostEqual(room.sources[0].age, 1.35)
        self.assertFalse(room.start_ingest())
        advance(room, 1.66)
        self.assertTrue(room.start_ingest())
        age = room.sources[0].age
        advance(room, .7)
        self.assertEqual(room.selected, 'wind')
        self.assertGreater(room.sources[0].age, age)
        self.assertFalse(room.start_ingest())

    def test_old_wind_room_save_relocates_the_ranged_enemy_without_resetting_player(self):
        room = Room(stage=4)
        room.player.x, room.player.y, room.player.hp = 10.75, 14.3, 76
        room.vine_time = room.vine_gate['burnDuration']
        room.enemies[0].hp = 23
        room.enemies[-1].hp = 17
        room.sources[0].phase, room.sources[0].age = 'gathering', 1.3
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
            record['state']['map_revision'] = 5
            record['state']['enemies'][0].update(x=11.7,y=13.8)
            record['state']['enemies'][-1].update(x=19.4, y=8.4, element='earth', attack_element='earth')
            restore(record, room)
        ranged = room.enemies[0]
        self.assertLess(ranged.x, room.windmill['origin'][0] - 3)
        self.assertTrue(room.fits(ranged.x,ranged.y,safe=True))
        self.assertEqual(ranged.hp, 23)
        neutral = room.enemies[-1]
        self.assertEqual((neutral.element, neutral.hp), ('neutral', 17))
        self.assertTrue(room.fits(neutral.x, neutral.y, safe=True))
        self.assertGreater(neutral.y, room.acquisition['bridge'][3])
        self.assertEqual(room.sources[0].phase, 'sealed')
        self.assertEqual((room.player.x,room.player.y,room.player.hp), (10.75,14.3,76))
        self.assertTrue(room.vine_open)

    def test_counterweight_stops_before_closed_vines_between_cells(self):
        room = Room(stage=4)
        room.inventory['wind'] = 1
        room.selected = 'wind'
        room.player.x, room.player.y, room.player.facing = 11.5, 22.5, 'up'
        self.assertTrue(room.skill())
        advance(room, 1.2)
        self.assertFalse(room.vine_open)
        self.assertEqual(room.block, (11.5, 18.5))
        self.assertIsNone(room.block_direction)

    def test_ledge_stops_a_wrong_push_and_the_block_can_be_reset(self):
        room = Room(stage=4)
        room.inventory['wind'] = 1
        room.selected = 'wind'
        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x, y - 1.25, 'down'
        self.assertTrue(room.skill())
        advance(room, .9)
        self.assertGreater(room.block[1], y)
        self.assertEqual(room.block, (x, 27.5))
        self.assertFalse(room.plate_pressed)
        room.player.x, room.player.y = room.puzzle['reset']
        room.update({'connect'}, .01)
        self.assertEqual(room.block, (x, y))

    def test_counterweight_has_no_shortcut_in_four_pushes(self):
        room = Room(stage=4)
        room.vine_time = room.vine_gate['burnDuration']
        for actor in (room.player, *room.enemies):
            actor.active = False
        frontier = {room.block}
        visited = set(frontier)
        for _ in range(4):
            reached = set()
            for point in frontier:
                for facing in ('up', 'down', 'left', 'right'):
                    room.block, room.block_direction = point, facing
                    for _ in range(100):
                        room.update_puzzle(.05)
                        if room.block_direction is None:
                            break
                    self.assertIsNone(room.block_direction)
                    self.assertFalse(room.plate_pressed)
                    reached.add(room.block)
            frontier = reached - visited
            visited.update(frontier)

    def test_legacy_counterweight_keeps_bridge_completion_and_windmill_progress(self):
        room = Room(stage=4)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
        state = record['state']
        state['map_revision'] = 8
        state['sources'][0].update(phase='gathering', age=.8)
        for enemy in state['enemies']:
            enemy.update(active=False, hp=0)
        state['stone_puzzle'].update(block=[14.5, 20.5], direction='right')
        state['player'].update(x=16.5, y=20.5, hp=76)
        restore(record, room)
        self.assertEqual(room.block, tuple(room.puzzle['start']))
        self.assertIsNone(room.block_direction)
        self.assertEqual((room.sources[0].phase, room.sources[0].age), ('gathering', .8))
        self.assertTrue(room.fits(room.player.x, room.player.y, safe=True))
        self.assertEqual(room.player.hp, 76)

        state['sources'][0].update(phase='consumed', age=0)
        state['inventory']['wind'] = 1
        state['stone_puzzle'].update(block=[12.5, 24.5], direction=None, pressed=True,
                                     gate_time=room.gate_open_seconds)
        restore(record, room)
        self.assertEqual(room.block, tuple(room.puzzle['plate']))
        self.assertTrue(room.plate_pressed)
        self.assertEqual(room.tile(18, 15), 0)

    def test_wind_pushes_earth_off_the_open_edge_without_direct_damage(self):
        room = Room(stage=4)
        enemy = room.enemies[-1]
        enemy.element = 'earth'
        room.player.x, room.player.y, room.player.facing = 22.3, 8.5, 'right'
        enemy.x, enemy.y = 23.4, 8.5
        room.inventory['wind'] = 1
        room.selected = 'wind'
        self.assertTrue(room.skill())
        advance(room, 1.5)
        self.assertFalse(enemy.active)
        self.assertEqual(enemy.hp, enemy.max_hp)
