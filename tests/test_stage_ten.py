import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.boss import (DASH_DISTANCE, DASH_SECONDS, DEFEAT_SECONDS, FORMS, GATE_SECONDS,
                      GUARDIAN_DRAW_UNIT, GUARDIAN_SHOT_LIFT,
                      MIXED_INGEST_BITE, MIXED_INGEST_SECONDS, SUMMON_SECONDS, RITUAL,
                      TRANSFORM_MIST_SECONDS, TRANSFORM_WARNING_SECONDS,
                      WATER_GAPS, WATER_RING_DELAY)
from src.combat import Projectile
from src.elements import WEAKNESS
from src.room import EarthTerrain, Room
from src.savegame import SaveStore, restore


def advance(room, seconds):
    for _ in range(round(seconds * 120)):
        room.update(set(), 1/120)


def enter_battle(room):
    guardian = room.guardian
    guardian.ritual = 5
    guardian.summon = SUMMON_SECONDS
    guardian.wind_y = guardian.spec['windPlateY']
    room.enemies[0].active = True
    return guardian, room.enemies[0]


class GuardianRoomTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=10)

    def test_pedestals_require_placement_then_return_the_orbs(self):
        room = self.room
        guardian = room.guardian
        x,y = guardian.spec['devices'][0]
        room.projectiles.append(Projectile(x,y+.2,0,-1,'hero',8,1,15,element='water'))
        room.update_projectiles(.05)
        self.assertEqual(guardian.ritual, 0)
        room.player.x, room.player.y = x, y
        room.restore_selected_element('fire')
        room.update({'connect'}, 1/120)
        self.assertEqual(guardian.ritual, 0)
        self.assertEqual(room.inventory['water'], 1)
        for index in (2, 0, 3, 1, 4):
            room.player.x, room.player.y = guardian.spec['devices'][index]
            room.restore_selected_element(RITUAL[index])
            room.update({'connect'}, 1/120)
        self.assertEqual(guardian.ritual, 5)
        self.assertFalse(any(room.inventory.values()))
        self.assertTrue(guardian.summoning)
        room.update({'ingest'}, 1/120)
        self.assertEqual(len(guardian.placed), 5)
        before_shock = (room.player.x, room.player.y)
        advance(room, SUMMON_SECONDS)
        self.assertTrue(guardian.battle)
        self.assertNotEqual((room.player.x, room.player.y), before_shock)
        for element, pedestal in zip(RITUAL, guardian.spec['devices']):
            x, y, phase = guardian.orb_flight(element)
            self.assertEqual(phase, 1)
            self.assertNotEqual((x, y), tuple(pedestal))
            self.assertTrue(room.fits(x, y, safe=True))
        room.player.x, room.player.y = guardian.orb_flight('lightning')[:2]
        room.update({'ingest'}, 1/120)
        self.assertEqual((room.selected, room.inventory['lightning']), ('lightning', 1))
        self.assertNotIn('lightning', guardian.placed)
        self.assertFalse(room.exit_open)

    def test_projectiles_hit_both_arms_and_legs_of_every_form(self):
        room = self.room
        guardian,actor = enter_battle(room)
        for form in FORMS:
            guardian.form = actor.element = form
            for i,(px,py) in enumerate(((80,209),(240,209),(121,247),(195,247),(29,209))):
                with self.subTest(form=form,point=(px,py)):
                    x = actor.x+(px-160)/GUARDIAN_DRAW_UNIT
                    y = actor.y+(py-264)/GUARDIAN_DRAW_UNIT+GUARDIAN_SHOT_LIFT
                    prior = actor.hp
                    room.projectiles = [Projectile(x,y+.02,0,-1,'hero',8,1,15,element=WEAKNESS[form])]
                    room.update_projectiles(.005)
                    self.assertEqual(actor.hp,prior-15 if i<4 else prior)
                    self.assertGreater(((x-actor.x)**2+(y-actor.y)**2)**.5,.42)

    def test_charged_lightning_skips_the_guardian_during_transformation(self):
        room = self.room
        guardian, actor = enter_battle(room)
        guardian.form = actor.element = 'water'
        room.player.x, room.player.y, room.player.facing = 15, 13.25, 'up'
        room.selected = 'lightning'
        room.lightning_charged = True
        guardian.start_transform(room, actor)
        self.assertTrue(room.start_attack(room.player))
        room.attack_tick(room.player, room.tuning.attack_event)
        self.assertEqual(actor.hp, actor.max_hp)
        self.assertTrue(room.lightning_charged)
        self.assertFalse(room.lightning_path)
        self.assertEqual([shot.element for shot in room.projectiles], ['lightning'])

    def test_water_wave_foam_hits_outside_the_old_point_radius(self):
        room = self.room
        guardian, actor = enter_battle(room)
        guardian.form = actor.element = 'water'
        room.player.x, room.player.y = 16, 13.85
        room.projectiles = [Projectile(16, 13, 1, 0, 'enemy', 4.4, 6, 10, age=1.8, element='water')]
        room.update_projectiles(.01)
        self.assertEqual(room.player.hp, room.player.max_hp - 10)
        self.assertFalse(room.projectiles)

    def test_water_wave_edge_stops_on_stone_and_earth_walls(self):
        for origin, player, earth_bounds in (
            ((5.35, 9.58), (9.1, 8.95), None),
            ((9.85, 10.18), (11.65, 9.60), (10.4, 9.1, 11.05, 9.9)),
        ):
            with self.subTest(earth_wall=earth_bounds is not None):
                room = Room(stage=10)
                if earth_bounds:
                    room.earth_terrain.append(EarthTerrain('wall', earth_bounds, room.earth_seconds))
                room.player.x, room.player.y = player
                shot = Projectile(*origin, 1, 0, 'enemy', 4.4, 10, 10, age=1.40, element='water')
                room.projectiles.append(shot)
                for _ in range(140):
                    room.update_projectiles(1 / 120)
                self.assertFalse(shot.active)
                self.assertEqual(room.player.hp, room.player.max_hp)
                self.assertNotEqual(room.tile(shot.x, shot.y, airborne=True), 3)
                self.assertIn('impact', room.sound_events)

    def test_water_wave_uses_open_space_and_does_not_hit_destroyed_cover(self):
        for destroyed, y in ((False, 10.55), (True, 9.58)):
            with self.subTest(destroyed=destroyed):
                room = Room(stage=10)
                if destroyed:
                    room.guardian.broken_cover.add(0)
                room.player.x, room.player.y = 9.1, y
                room.projectiles.append(Projectile(5.35, y, 1, 0, 'enemy', 4.4, 10, 10,
                                                   age=1.40, element='water'))
                for _ in range(140):
                    room.update_projectiles(1 / 120)
                self.assertEqual(room.player.hp, room.player.max_hp - 10)

    def test_water_rings_hit_aim_line_but_leave_each_warned_gap_open(self):
        for index, gap in enumerate(WATER_GAPS):
            for offset, damage in ((0, 10), (gap, 0)):
                with self.subTest(ring=index, offset=offset):
                    room = Room(stage=10)
                    guardian, actor = enter_battle(room)
                    guardian.form = actor.element = 'water'
                    guardian.heading = math.pi / 2
                    angle = guardian.heading + offset
                    room.player.x = actor.x + 4 * math.cos(angle)
                    room.player.y = actor.y + 4 * math.sin(angle)
                    release = guardian.clip('attack').events['release'] + index * WATER_RING_DELAY
                    guardian.attack_age = release - .01
                    guardian.update_attack(room, actor, .02)
                    for _ in range(120):
                        room.update_projectiles(1 / 120)
                    self.assertEqual(room.player.hp, room.player.max_hp - damage)

    def test_wind_dash_breaks_cover_and_earth_wall_on_contact_and_saves_it(self):
        room = self.room
        guardian, actor = enter_battle(room)
        guardian.form = actor.element = 'wind'
        guardian.cooldown = 0
        actor.x, actor.y = 11, 8.94
        room.player.x, room.player.y = 5.45, actor.y
        earth_wall = EarthTerrain('wall', (9.2, 8.35, 9.84, 9.48), room.earth_seconds)
        room.earth_terrain.append(earth_wall)

        room.update(set(), 1 / 120)
        predicted_x, _ = guardian.dash_endpoint(room, actor.x, actor.y, DASH_DISTANCE)
        release = guardian.clip('attack').events['release']
        advance(room, release - .04)
        self.assertEqual(guardian.broken_cover, set())
        self.assertIn(earth_wall, room.earth_terrain)
        self.assertEqual(room.tile(7, actor.y), 3)
        self.assertLess(predicted_x, 6)

        advance(room, .24)
        self.assertEqual(guardian.broken_cover, {0})
        self.assertNotIn(earth_wall, room.earth_terrain)
        self.assertEqual(len(guardian.dash_debris), 2)
        self.assertEqual(room.tile(7, actor.y), 0)
        advance(room, DASH_SECONDS)
        self.assertAlmostEqual(actor.x, predicted_x, delta=.08)
        self.assertEqual(room.player.hp, room.player.max_hp - 10)

        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory) / 'continue.json')
            store.write(room)
            resumed = Room()
            restore(store.load(), resumed)
        self.assertEqual(resumed.guardian.broken_cover, {0})
        self.assertEqual(resumed.tile(7, actor.y), 0)
        resumed.reset()
        self.assertEqual(resumed.tile(7, actor.y), 3)

    def test_wind_dash_stops_at_a_pit_beyond_breakable_cover(self):
        room = self.room
        guardian, _ = enter_battle(room)
        guardian.heading = math.pi
        guardian.pits.append((5.65, 8.94))
        x, y = guardian.dash_endpoint(room, 11, 8.94, DASH_DISTANCE, shatter=True)
        self.assertEqual(guardian.broken_cover, {0})
        self.assertTrue(room.fits(x, y, safe=True))
        self.assertGreater(x, 6.5)
        self.assertLess(x, 7)

    def test_shared_health_and_timed_random_swap(self):
        room = self.room
        guardian,actor = enter_battle(room)
        self.assertTrue(room.damage(actor,160))
        self.assertEqual(actor.hp,290)
        self.assertLess(guardian.swap,0)
        advance(room, guardian.spec['formSeconds'] - TRANSFORM_WARNING_SECONDS - .08)
        self.assertIsNone(guardian.warning_form)
        with patch('src.boss.random.choice',return_value='water') as choice:
            advance(room, .09)
            self.assertEqual(guardian.warning_form, 'water')
            self.assertEqual(guardian.element, 'fire')
            self.assertIsNone(guardian.next_form)
            advance(room, guardian.form_left - .08)
            self.assertEqual(guardian.warning_form, 'water')
            self.assertLess(guardian.swap, 0)
            room.projectiles.append(Projectile(15,12,0,1,'enemy',8,3,10,element='fire'))
            advance(room, .09)
        choice.assert_called_once_with(['wind','earth','lightning','water'])
        self.assertIsNone(guardian.warning_form)
        self.assertEqual((guardian.next_form,actor.hp),('water',290))
        self.assertFalse(any(p.owner=='enemy' for p in room.projectiles))
        advance(room,guardian.clip('transform').duration)
        self.assertEqual((guardian.form,actor.element,actor.hp),('water','water',290))
        self.assertTrue(room.boss_exposed)

    def test_mist_restores_target_and_starts_each_transform_on_arrival(self):
        for current, target in zip(FORMS, FORMS[1:] + FORMS[:1]):
            with self.subTest(target=target), TemporaryDirectory() as directory:
                room = Room(stage=10)
                guardian, actor = enter_battle(room)
                guardian.form = actor.element = current
                guardian.form_left = TRANSFORM_WARNING_SECONDS
                with patch('src.boss.random.choice', return_value=target):
                    advance(room, TRANSFORM_WARNING_SECONDS - TRANSFORM_MIST_SECONDS / 2)
                self.assertEqual(guardian.warning_form, target)
                self.assertLess(guardian.form_left, TRANSFORM_MIST_SECONDS)
                self.assertTrue(guardian.vulnerable)

                store = SaveStore(Path(directory) / 'continue.json')
                store.write(room)
                resumed = Room()
                restore(store.load(), resumed)
                g = resumed.guardian
                self.assertEqual(g.warning_form, target)
                self.assertEqual(g.form_left, guardian.form_left)
                with patch('src.boss.random.choice') as choice:
                    advance(resumed, g.form_left - 1/120)
                    self.assertEqual(g.element, current)
                    self.assertLess(g.swap, 0)
                    resumed.update(set(), g.form_left)
                    choice.assert_not_called()
                self.assertEqual(g.swap, 0)
                self.assertEqual(g.next_form, target)
                self.assertIsNone(g.warning_form)

    def test_continue_after_burning_guardian_transforms_or_falls(self):
        for hp in (30, 450):
            with self.subTest(hp=hp), TemporaryDirectory() as tmp:
                room = Room(stage=10)
                guardian, actor = enter_battle(room)
                guardian.form = actor.element = 'wind'
                actor.hp = hp
                for _ in range(2 if hp == 30 else 1):
                    room.projectiles.append(
                        Projectile(actor.x, actor.y+.01, 0, -1, 'hero', 8, 2, 15, element='fire'))
                    room.update_projectiles(1/120)
                if hp != 30:
                    self.assertGreater(actor.burn_ticks, 0)
                    guardian.form_left = 1/120
                    room.update(set(), 1/120)
                    self.assertEqual(guardian.swap, 0)
                else:
                    self.assertGreaterEqual(guardian.fall, 0)
                self.assertEqual((actor.burn_ticks, actor.burn_delay), (0, 0))

                store = SaveStore(Path(tmp) / 'continue.json')
                # 수정 전 자동 저장도 그대로 이어갈 수 있어야 한다.
                actor.burn_delay = .4
                store.write(room)
                record = store.load()
                self.assertIsNotNone(record)
                restored = Room(stage=10)
                restore(record, restored)
                self.assertEqual((restored.enemies[0].burn_ticks, restored.enemies[0].burn_delay), (0, 0))

    def test_continue_retains_selected_form_and_timer(self):
        room = self.room
        guardian, actor = enter_battle(room)
        room.damage(actor,109)
        guardian.form_left = .1
        with patch('src.boss.random.choice',return_value='lightning'):
            advance(room,.11)
        advance(room,guardian.clip('transform').events['elementChange']+.025)
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(room)
            resumed = Room()
            restore(store.load(),resumed)
        self.assertEqual(resumed.guardian.record(),guardian.record())
        self.assertEqual((resumed.enemies[0].element,resumed.enemies[0].hp),('lightning',341))
        advance(resumed,1)
        self.assertEqual(resumed.guardian.form,'lightning')
        self.assertIsNone(resumed.guardian.next_form)

    def test_zero_shared_health_opens_only_the_center_of_the_gate(self):
        room = self.room
        guardian, actor = enter_battle(room)
        guardian.form = actor.element = 'wind'
        self.assertTrue(room.damage(actor,450))
        self.assertFalse(actor.active)
        self.assertFalse(room.fits(15,2.3,safe=True))
        advance(room,DEFEAT_SECONDS+GATE_SECONDS+.06)
        self.assertTrue(room.exit_open)
        self.assertTrue(room.fits(15,2.3,safe=True))
        self.assertFalse(room.fits(13.6,2.3,safe=True))

    def test_final_reward_requires_mixing_and_leaving_after_continue(self):
        room = self.room
        _, actor = enter_battle(room)
        room.damage(actor, actor.hp)
        self.assertIsNone(room.final_reward)
        advance(room, DEFEAT_SECONDS + GATE_SECONDS + .06)
        reward = room.final_reward
        self.assertTrue(room.fits(*reward, safe=True))
        room.update({'ingest'}, 1/120)
        self.assertIsNone(room.outcome)
        exit_point = room.data['plannedExit']
        room.player.x, room.player.y = exit_point['x'], exit_point['y']
        advance(room, .1)
        self.assertIsNone(room.outcome)
        room.player.x, room.player.y = reward
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory) / 'continue.json')
            store.write(room)
            resumed = Room()
            restore(store.load(), resumed)
        self.assertEqual(resumed.final_reward, reward)
        self.assertEqual(reward, (actor.x, actor.y))
        self.assertTrue(resumed.can_claim_final_reward)
        resumed.update({'ingest'}, 1/120)
        self.assertFalse(resumed.guardian.reward_tasted)
        self.assertTrue(resumed.insert_final_orb('water'))
        self.assertFalse(resumed.insert_final_orb('water'))
        self.assertFalse(resumed.guardian.reward_loaded)
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(resumed)
            restore(store.load(), resumed)
        self.assertEqual(resumed.guardian.reward_orbs, {'water'})
        for element in RITUAL[1:]:
            self.assertTrue(resumed.insert_final_orb(element))
        self.assertFalse(any(resumed.inventory.values()))
        self.assertTrue(resumed.guardian.reward_loaded)
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(resumed)
            restore(store.load(), resumed)
        resumed.update({'ingest'}, 1/120)
        self.assertFalse(resumed.guardian.reward_tasted)
        self.assertEqual(resumed.guardian.reward_scene_elapsed, 0)
        resumed.guardian.advance_reward_scene(MIXED_INGEST_BITE)
        self.assertTrue(resumed.guardian.reward_tasted)
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(resumed)
            restore(store.load(), resumed)
        self.assertEqual(resumed.guardian.reward_scene_elapsed, MIXED_INGEST_BITE)
        resumed.guardian.advance_reward_scene(MIXED_INGEST_SECONDS)
        self.assertIsNone(resumed.guardian.reward_scene_elapsed)
        self.assertIsNone(resumed.outcome)
        resumed.update({'attack'}, 1/120)
        advance(resumed, .4)
        self.assertEqual([shot.element for shot in resumed.projectiles], ['mixed'])
        shot, = resumed.projectiles
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory) / 'continue.json')
            store.write(resumed)
            restore(store.load(), resumed)
        self.assertEqual(resumed.projectiles, [shot])
        advance(resumed, 1)
        self.assertFalse(resumed.projectiles)
        self.assertIsNone(resumed.outcome)
        resumed.update({'attack'}, 1/120)
        advance(resumed, .4)
        self.assertEqual([shot.element for shot in resumed.projectiles], ['mixed'])
        resumed.player.x, resumed.player.y = exit_point['x'], 2.08
        advance(resumed, .1)
        self.assertIsNone(resumed.outcome)
        resumed.player.x, resumed.player.y = exit_point['x'], exit_point['y']
        advance(resumed, .1)
        self.assertEqual(resumed.outcome, 'clear')
        self.assertIsNone(resumed.final_reward)

    def test_debug_boss_starts_battle_at_one_hp_and_still_drops_reward(self):
        room = self.room
        guardian, boss = room.guardian, room.enemies[0]
        self.assertEqual(boss.hp, 450)
        room.update({'debug-clear'}, 1/120)
        self.assertTrue(guardian.vulnerable and boss.active)
        self.assertEqual(boss.hp, 1)
        self.assertIsNone(room.final_reward)
        self.assertEqual(guardian.placed, set(RITUAL))
        self.assertFalse(any(room.inventory.values()))
        room.player.x, room.player.y = guardian.orb_flight('water')[:2]
        room.update({'ingest'}, 1/120)
        self.assertEqual(room.inventory['water'], 1)
        room.update({'debug-clear'}, 1/120)
        self.assertEqual(room.inventory['water'], 1)
        self.assertEqual(guardian.placed, set(RITUAL)-{'water'})
        self.assertTrue(room.damage(boss, 1, attack_element='water'))
        room.update({'debug-clear'}, 1/120)
        self.assertFalse(boss.active)
        origin = room.player.x, room.player.y
        for _ in range(90):
            room.update({'w', 'attack'}, 1/120)
        self.assertEqual((room.player.x, room.player.y), origin)
        self.assertTrue(guardian.collapsing)
        self.assertIsNone(room.final_reward)
        advance(room, DEFEAT_SECONDS-.75+.05)
        self.assertEqual(room.sound_events.count('boss-shatter'), 1)
        self.assertEqual(room.final_reward, (boss.x, boss.y))

    def test_earlier_core_save_keeps_health_and_ritual(self):
        room = self.room
        guardian,actor = enter_battle(room)
        guardian.form = actor.element = 'earth'
        room.damage(actor,232)
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
        boss = record['state']['boss']
        for key in ('form','next_form','form_left'):
            del boss[key]
        boss['core'] = 2
        resumed = Room()
        restore(record,resumed)
        self.assertEqual((resumed.guardian.ritual,resumed.guardian.form,resumed.enemies[0].hp),
                         (5,'earth',218))
        self.assertEqual(resumed.guardian.form_left,guardian.spec['formSeconds'])

    def test_old_boss_save_starts_at_the_new_entrance(self):
        room = self.room
        with TemporaryDirectory() as directory:
            store = SaveStore(Path(directory)/'continue.json')
            store.write(room)
            record = json.loads(store.path.read_text(encoding='utf-8'))
        record['state'].pop('map_revision')
        record['state']['player'].update(x=32,y=20,hp=52)
        record['state']['selected'] = 'wind'
        resume = Room(stage=9)
        restore(record,resume)
        self.assertEqual((resume.player.x,resume.player.y,resume.player.hp),(15,22.5,52))
        self.assertEqual(resume.selected,'wind')
        self.assertEqual(resume.guardian.ritual,0)


if __name__ == '__main__':
    unittest.main()
