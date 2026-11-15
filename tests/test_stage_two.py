"""두 번째 방, 원천·섭취·물/무속성 상성 및 보관/소모 시나리오."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.room import Room, EarthTerrain
from src.elements import ELEMENTS,BEATS,WEAKNESS,Source
from src.combat import Projectile
from src.savegame import SaveStore,restore


def advance(room,seconds,keys=()):
    for _ in range(round(seconds*120)):
        room.update(set(keys),1/120)


class StageTwoTests(unittest.TestCase):
    def test_approved_layout_and_enemy_elements(self):
        room = Room(stage=2)
        self.assertEqual(room.stage,2)
        self.assertEqual(Counter(e.element for e in room.enemies), {'neutral':2,'fire':1})
        self.assertEqual([source.phase for source in room.sources], ['sealed'])
        self.assertEqual((room.player.x,room.player.y), (16.5,25.7))

    def test_fire_group_waits_for_upper_arena(self):
        room = Room(stage=2)
        enemy = room.enemies[-1]
        room.player.x, room.player.y = 16.5, 14.5
        self.assertFalse(room.enemy_awake(enemy))
        room.inventory['water'] = 1
        self.assertTrue(room.enemy_awake(enemy))

    def test_sluice_requires_guard_clearance_and_interaction(self):
        room = Room(stage=2)
        room.player.x, room.player.y = room.acquisition['switch']
        room.update({'connect'}, .01)
        self.assertEqual(room.sources[0].phase, 'sealed')
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.update(set(), .01)
        self.assertEqual(room.sources[0].phase, 'sealed')
        room.update({'connect'}, .01)
        self.assertEqual(room.sources[0].phase, 'descending')
        self.assertFalse(room.exit_open)

    def test_reservoir_descent_is_saved_and_orb_is_edible_only_after_landing(self):
        room = Room(stage=2)
        room.player.x, room.player.y = room.acquisition['switch']
        for enemy in room.enemies[:2]:
            room.damage(enemy, enemy.hp)
        room.update({'connect'}, .01)
        orb = room.sources[0]
        room.player.x, room.player.y = orb.x + 1.15, orb.y
        advance(room, .65, ('ingest',))
        self.assertEqual(orb.phase, 'descending')
        self.assertFalse(room.start_ingest())
        self.assertEqual(room.inventory['water'], 0)
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder) / 'continue.json')
            store.write(room)
            restored = Room()
            restore(store.load(), restored)
        self.assertAlmostEqual(restored.sources[0].age, orb.age)
        self.assertEqual(restored.sources[0].phase, 'descending')
        advance(restored, 1.16)
        self.assertTrue(restored.start_ingest())
        advance(restored, .7)
        self.assertEqual(restored.inventory['water'], 1)
        self.assertFalse(restored.start_ingest())

    def test_bridge_cannot_be_reached_past_first_fire_using_the_west_corridor(self):
        room = Room(stage=2)
        room.player.x, room.player.y = room.acquisition['switch']
        self.assertNotIn((16,16), room.distance_field())
        room.player.x, room.player.y = 16.5, 21.7
        self.assertNotIn((16,16), room.distance_field())
        room.extinguished.add(0)
        self.assertIn((16,16), room.distance_field())
        self.assertNotIn((16,10), room.distance_field())
        room.extinguished.add(1)
        self.assertIn((16,10), room.distance_field())

    def test_later_fire_requires_first_fire_even_if_hit_from_the_side(self):
        room = Room(stage=2)
        for expected in (set(), {0, 1}):
            room.projectiles.append(Projectile(12.5, 13, 1, 0, 'hero', 8, 6, 15, element='water'))
            for _ in range(12):
                room.update_projectiles(.05)
            self.assertEqual(room.extinguished, expected)
            room.extinguished.add(0)

    def test_old_room_two_save_moves_orb_and_recovers_from_removed_path(self):
        room = Room(stage=2)
        room.player.x, room.player.y, room.player.hp = 14.5, 17.2, 76
        room.safe = 14.5, 17.2, 'left'
        room.sources[0].phase = 'orb'
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder)/'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
            record['state']['sources'][0].update(x=11.8, y=17.72)
            restore(record, room)
        self.assertEqual((room.sources[0].x,room.sources[0].y), (9.55,14.67))
        self.assertEqual(room.sources[0].phase, 'orb')
        self.assertEqual(room.player.hp, 76)
        self.assertTrue(room.fits(room.player.x,room.player.y,safe=True))
        self.assertGreater(room.player.y, room.fire_barriers[0][3])

    def test_source_three_hits_persist_then_break_once_and_keep_orb(self):
        source = Source('test',0,0)
        for i in range(2):
            self.assertTrue(source.hit('neutral'))
            source.update(9)
            self.assertEqual(source.phase,f'damaged{i+1}')
            self.assertEqual(source.hp,2-i)
        self.assertTrue(source.hit('neutral'))
        self.assertEqual(source.phase,'breaking')
        self.assertFalse(source.hit('neutral'))
        source.update(.6)
        self.assertEqual(source.phase,'orb')
        source.update(999)
        self.assertEqual(source.phase,'orb')

    def test_source_weakness_and_same_element_rule_for_all_elements(self):
        for target in ELEMENTS:
            for attack in ('neutral',*ELEMENTS):
                source = Source('test',0,0,target)
                source.hit(attack)
                self.assertEqual(source.hp,0 if attack == WEAKNESS[target] else 2)

    def test_projectile_damages_source_without_ingesting_it(self):
        room = Room()
        for e in room.enemies:
            e.active = False
        room.player.x,room.player.y,room.player.facing = 10,19.5,'up'
        room.sources.append(Source('test', 10, 18.25))
        room.start_attack(room.player)
        advance(room,.6)
        self.assertEqual(room.sources[0].phase,'damaged1')
        self.assertEqual(room.inventory['water'],0)
        self.assertFalse(room.start_ingest())

    def test_ingestion_adds_one_unit_once_and_changes_form_after_animation(self):
        room = Room(stage=2)
        source = room.sources[0]
        source.hp,source.phase = 0,'orb'
        room.player.x,room.player.y = source.x,source.y+1
        self.assertTrue(room.start_ingest())
        advance(room,.4)
        self.assertEqual(source.phase,'consumed')
        self.assertEqual(room.inventory['water'],0)
        advance(room,.4)
        self.assertEqual(room.inventory['water'],1)
        self.assertEqual(room.selected,'water')
        self.assertFalse(room.start_ingest())
        advance(room,1)
        self.assertEqual(room.inventory['water'],1)

    def test_ingest_requires_nearby_released_orb_not_jar_or_orb_behind_wall(self):
        room = Room(stage=2)
        self.assertFalse(room.start_ingest())
        source = room.sources[0]
        source.hp,source.phase = 0,'orb'
        self.assertFalse(room.start_ingest())
        room.player.x,room.player.y = source.x, source.y + .9
        room.earth_terrain.append(EarthTerrain('wall',
            (source.x-.3, source.y+.22, source.x+.3, source.y+.42), 1))
        self.assertFalse(room.start_ingest())
        room.earth_terrain.clear()
        self.assertTrue(room.start_ingest())

    def test_water_skill_repeats_without_consuming_the_unlock(self):
        room = Room(stage=2)
        room.inventory['water'],room.selected = 2,'water'
        self.assertFalse(room.heal())
        self.assertEqual(room.inventory['water'],2)
        room.player.hp = 65
        self.assertTrue(room.heal())
        self.assertEqual(room.player.hp,85)
        self.assertEqual(room.inventory['water'],2)
        self.assertTrue(room.heal())
        self.assertEqual(room.player.hp,100)
        self.assertEqual(room.selected,'water')
        self.assertEqual(room.inventory['water'],2)

    def test_space_keeps_cast_element_after_switching(self):
        room = Room(stage=2)
        room.inventory['water'],room.selected,room.player.hp = 1,'water',50
        room.start_attack(room.player)
        self.assertEqual(room.inventory['water'],1)
        room.inventory['fire'] = 1
        room.select_element(1)
        self.assertEqual(room.selected,'fire')
        advance(room,.3)
        self.assertTrue(any(s.element == 'water' and s.owner == 'hero' for s in room.projectiles))

    def test_all_attacks_strong_against_neutral_and_element_cycle_still_blocks_others(self):
        for attack in ('neutral',*ELEMENTS):
            for target in ('neutral',*ELEMENTS):
                room = Room()
                for e in room.enemies:
                    e.active = False
                enemy = room.enemies[0]
                enemy.active,enemy.element,enemy.x,enemy.y = True,target,10,19
                damage = room.tuning.neutral_damage if attack == 'neutral' else room.tuning.elemental_damage
                room.projectiles.append(Projectile(9.7,19,1,0,'hero',7,1,damage,element=attack))
                room.update_projectiles(1/120)
                expected = 15 if target == 'neutral' else 5 if attack == 'neutral' else 15 if BEATS[attack] == target else 0
                self.assertEqual(enemy.hp,30-expected,(attack,target))
                if expected == 0:
                    self.assertEqual(enemy.knockback_left,0)
                    self.assertEqual(enemy.hit_flash,0)
                if attack != 'neutral':
                    self.assertEqual(enemy.knockback_left,0)

    def test_stage_two_save_round_trip_sources_inventory_and_pending_ingestion(self):
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder)/'continue.json')
            room = Room(stage=2)
            for e in room.enemies:
                e.active = False
            room.sources[0].hp,room.sources[0].phase = 0,'orb'
            orb = room.sources[0]
            room.player.x,room.player.y = orb.x,orb.y + .8
            room.start_ingest()
            advance(room,.4)
            store.write(room)
            record = store.load()
            self.assertEqual(record['stage'],2)
            result = Room()
            restore(record,result)
            self.assertEqual(result.stage,2)
            self.assertEqual(result.sources[0].phase,'consumed')
            advance(result,.4)
            self.assertEqual(result.inventory['water'],1)
            self.assertEqual(result.selected,'water')
            advance(result,1)
            self.assertEqual(result.inventory['water'],1)

    def test_version_one_checkpoint_is_migrated_without_losing_health(self):
        with TemporaryDirectory() as folder:
            store = SaveStore(Path(folder)/'continue.json')
            room = Room()
            room.player.hp = 73
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
            record['version'] = 1
            for actor in [record['state']['player'],*record['state']['enemies']]:
                actor.pop('element'); actor.pop('attack_element')
            for key in ('sources','inventory','selected','fire_aggro','ingest_elapsed','ingest_source','ingest_consumed','ingest_form'):
                record['state'].pop(key)
            store.path.write_text(json.dumps(record),encoding='utf-8')
            restored = Room()
            restore(store.load(),restored)
            self.assertEqual(restored.stage,1)
            self.assertEqual(restored.player.hp,73)
            self.assertEqual(restored.selected,'neutral')

    def test_reset_second_stage_reseals_the_orb(self):
        room = Room(stage=2)
        room.sources[0].hit('lightning')
        room.inventory['water'],room.selected = 2,'water'
        room.reset()
        self.assertEqual(room.stage,2)
        self.assertEqual([s.phase for s in room.sources], ['sealed'])
        self.assertEqual(room.inventory['water'],0)
        self.assertEqual(room.selected,'neutral')

    def test_enemy_routes_around_intact_water_source(self):
        room = Room()
        room.player.x,room.player.y = 9.5,9.5
        room.aggro = True
        room.sources.append(Source('test', 7, 9.5))
        enemy = room.enemies[0]
        enemy.x,enemy.y = 5.5,9.5
        for other in room.enemies[1:]:
            other.active = False
        for _ in range(12*120):
            room.update(set(),1/120)
            self.assertTrue(room.fits(enemy.x,enemy.y,safe=True))
        import math
        self.assertLess(math.hypot(enemy.x-room.player.x,enemy.y-room.player.y),1)


if __name__ == '__main__':
    unittest.main()
