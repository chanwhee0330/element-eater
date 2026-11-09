"""두 번째 방, 원천·섭취·물/무속성 상성 및 보관/소모 시나리오."""
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import asdict
import json
import unittest

from src.room import Room
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
        self.assertEqual(Counter(e.element for e in room.enemies),{'neutral':2,'fire':2})
        self.assertEqual(len(room.sources),2)
        self.assertEqual((room.player.x,room.player.y),(10,19.5))

    def test_fire_group_waits_for_upper_arena(self):
        room = Room(stage=2)
        before = [(e.x,e.y) for e in room.enemies if e.element == 'fire']
        advance(room,.4)
        self.assertTrue(room.aggro)
        self.assertFalse(room.fire_aggro)
        self.assertEqual(before,[(e.x,e.y) for e in room.enemies if e.element == 'fire'])
        room.player.x,room.player.y = 8,9
        advance(room,.1)
        self.assertTrue(room.fire_aggro)

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
        room = Room(stage=2)
        for e in room.enemies:
            e.active = False
        room.player.x,room.player.y,room.player.facing = 5.5,14.5,'up'
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
        room.player.x,room.player.y = 6.7,13.35
        self.assertTrue(room.start_ingest())

    def test_water_skill_heals_consumes_only_on_success_and_exhausts_to_neutral(self):
        room = Room(stage=2)
        room.inventory['water'],room.selected = 2,'water'
        self.assertFalse(room.heal())
        self.assertEqual(room.inventory['water'],2)
        room.player.hp = 65
        self.assertTrue(room.heal())
        self.assertEqual(room.player.hp,85)
        self.assertEqual(room.inventory['water'],1)
        self.assertTrue(room.heal())
        self.assertEqual(room.player.hp,100)
        self.assertEqual(room.selected,'neutral')
        self.assertEqual(room.inventory['water'],0)

    def test_space_does_not_consume_and_cast_element_survives_skill_exhaustion(self):
        room = Room(stage=2)
        room.inventory['water'],room.selected,room.player.hp = 1,'water',50
        room.start_attack(room.player)
        self.assertEqual(room.inventory['water'],1)
        self.assertTrue(room.heal())
        self.assertEqual(room.selected,'neutral')
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
            room.sources[1].hit('neutral')
            room.player.x,room.player.y = 5.5,13.35
            room.start_ingest()
            advance(room,.4)
            store.write(room)
            record = store.load()
            self.assertEqual(record['stage'],2)
            result = Room()
            restore(record,result)
            self.assertEqual(result.stage,2)
            self.assertEqual(result.sources[1].phase,'damaged1')
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

    def test_reset_second_stage_restores_source_and_clears_inventory(self):
        room = Room(stage=2)
        room.sources[0].hit('lightning')
        room.inventory['water'],room.selected = 2,'water'
        room.reset()
        self.assertEqual(room.stage,2)
        self.assertEqual([s.hp for s in room.sources],[3,3])
        self.assertEqual(room.inventory['water'],0)
        self.assertEqual(room.selected,'neutral')

    def test_enemy_routes_around_intact_water_source(self):
        room = Room(stage=2)
        room.player.x,room.player.y = 5.5,12.5
        room.aggro = True
        enemy = room.enemies[0]
        enemy.x,enemy.y = 5.5,17
        for other in room.enemies[1:]:
            other.active = False
        for _ in range(12*120):
            room.update(set(),1/120)
            self.assertTrue(room.fits(enemy.x,enemy.y,safe=True))
        import math
        self.assertLess(math.hypot(enemy.x-room.player.x,enemy.y-room.player.y),1)


if __name__ == '__main__':
    unittest.main()
