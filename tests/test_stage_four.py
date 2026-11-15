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

    def test_wind_orb_requires_vine_then_slides_plate_and_restores_moving_block(self):
        room = Room(stage=4)
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.update(set(), .01)
        self.assertEqual(room.sources[0].phase, 'sealed')
        room.player.x, room.player.y, room.player.facing = 10.2, 19.65, 'up'
        room.update({'attack'}, .01)
        advance(room, 1.4)
        self.assertTrue(room.vine_open)
        source, = room.sources
        self.assertEqual(source.phase, 'orb')
        room.player.x = source.x
        room.player.y = source.y
        room.update({'ingest'}, .01)
        advance(room, .7)
        self.assertEqual(room.selected, 'wind')

        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x - 2, y, 'right'
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
        advance(room, 1)
        self.assertEqual(room.tile(18, 15), 0)
        self.assertEqual(room.inventory['wind'], 1)
        room.player.x, room.player.y = 17.5, 17.7
        advance(room, 1.7, 'w')
        self.assertLess(room.player.y, 13)
        self.assertFalse(room.player.falling)

    def test_block_can_be_reset_after_pushing_it_in_the_wrong_direction(self):
        room = Room(stage=4)
        room.inventory['wind'] = 1
        room.selected = 'wind'
        x, y = room.block
        room.player.x, room.player.y, room.player.facing = x, y + 1.4, 'up'
        self.assertTrue(room.skill())
        advance(room, .9)
        self.assertLess(room.block[1], y)
        self.assertFalse(room.plate_pressed)
        room.player.x, room.player.y = room.puzzle['reset']
        room.update({'connect'}, .01)
        self.assertEqual(room.block, (x, y))

    def test_wind_pushes_earth_off_the_open_edge_without_direct_damage(self):
        room = Room(stage=4)
        enemy = room.enemies[-1]
        room.player.x, room.player.y, room.player.facing = 22.3, 8.5, 'right'
        enemy.x, enemy.y = 23.4, 8.5
        room.inventory['wind'] = 1
        room.selected = 'wind'
        self.assertTrue(room.skill())
        advance(room, 1.5)
        self.assertFalse(enemy.active)
        self.assertEqual(enemy.hp, enemy.max_hp)
