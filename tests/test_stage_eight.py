from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.room import Room
from src.savegame import SaveStore, restore


class StageEightTests(unittest.TestCase):
    def setUp(self):
        self.room = Room(stage=8)

    def tick(self, seconds, *keys):
        for _ in range(round(seconds*60)):
            self.room.update(set(keys), 1/60)

    def face(self, element, x, y, facing):
        self.room.selected = element
        player = self.room.player
        player.x, player.y, player.facing = x, y, facing

    def solve_transport(self):
        room = self.room
        self.face('fire',18,19.4,'up')
        self.tick(.9,'attack')
        self.tick(.8)
        self.assertTrue(room.vine_open)
        self.assertEqual(room.tile(12.5,16),4)
        self.face('earth',14.65,16,'left')
        self.tick(1/60,'skill')
        self.tick(1.35,'a')
        self.assertTrue(room.bridge_crossed)
        self.assertLess(room.player.x,11)
        self.face('wind',8.35,10.5,'right')
        self.tick(1.15,'skill')
        self.assertAlmostEqual(room.block[0],16.5)
        self.assertAlmostEqual(room.block[1],10.5)
        self.assertEqual(room.tile(22.5,16),3)
        self.face('wind',16.5,9.2,'down')
        self.tick(.9,'skill')
        self.assertTrue(room.plate_pressed)
        self.assertTrue(room.stone_gate_open)
        self.assertEqual(room.tile(22.5,16),0)
        self.assertEqual(room.tile(16.5,14.5),0)

    def test_counterweight_stops_at_thin_stone_wall(self):
        self.face('wind', 9.5, 11.5, 'up')
        self.tick(1.2, 'skill')
        self.assertEqual(self.room.block, (9.5, 5.5))
        self.face('wind', 10.3, 6.2, 'left')
        self.tick(1.2, 'skill')
        self.assertEqual(self.room.block, (9.5, 5.5))
        self.assertIsNone(self.room.block_direction)

    def test_transport_gates_and_each_laser(self):
        room = self.room
        self.assertFalse(room.sources)
        self.assertTrue(all(room.inventory.values()))
        self.solve_transport()
        self.face('earth',27.78,12.04,'right')
        self.assertNotIn((58,18),room.reference_distances())
        for index, cue in enumerate(room.quarry.config['wallCues']):
            x,y,facing = cue
            self.face('earth',x,y,facing)
            self.tick(.42,'w')
            beam_y = room.quarry.lasers[index][2]
            self.assertGreater(room.player.y,beam_y)
            self.face('earth',x,y,facing)
            self.tick(1/60,'skill')
            self.tick(.6,'w')
            beam = room.quarry.beams(room.earth_terrain)[index]
            self.assertNotEqual(beam[1],beam[3])
            self.assertLess(room.player.y,beam_y)
            if index==0:
                paths = room.reference_distances()
                self.assertIn((58,18),paths)
                self.assertNotIn((52,4),paths)

        with TemporaryDirectory() as temp:
            store = SaveStore(Path(temp)/'continue.json')
            store.write(room)
            restored = Room(stage=8)
            restore(store.load(),restored)
        self.assertEqual(restored.quarry.beams(restored.earth_terrain),room.quarry.beams(room.earth_terrain))
        self.room = restored
        self.tick(4.1)
        self.assertTrue(all(stop==receiver for _,stop,_,receiver in restored.quarry.beams(restored.earth_terrain)))
        self.assertFalse(restored.exit_open)
        for enemy in restored.enemies:
            restored.damage(enemy,enemy.max_hp)
        restored.player.x,restored.player.y = 26,1.85
        self.tick(.55)
        self.assertEqual(restored.outcome,'clear')

    def test_reconnecting_beam_returns_player_to_safe_bank(self):
        room = self.room
        x,y,facing = room.quarry.config['wallCues'][0]
        self.face('earth',x,y,facing)
        self.assertTrue(room.cast_earth())
        room.safe = (x,y,facing)
        room.player.y = room.quarry.lasers[0][2]
        room.earth_terrain[0].remaining = .001
        self.tick(.05)
        self.assertAlmostEqual(room.player.y,y)
        self.assertTrue(room.quarry.beams(room.earth_terrain)[0][1] == room.quarry.lasers[0][1])

    def test_wall_slot_accepts_normal_approach_positions_and_facings(self):
        room = self.room
        for index, (_, receiver, beam_y) in enumerate(room.quarry.lasers):
            for x in (28.25,28.5,28.75):
                for depth in (.45,.75,1.1):
                    for facing in ('up','down','left','right'):
                        with self.subTest(laser=index, x=x, depth=depth, facing=facing):
                            room.earth_terrain.clear()
                            self.face('earth',x,beam_y+depth,facing)
                            self.assertTrue(room.fits(x,beam_y+depth,safe=True))
                            self.assertTrue(room.cast_earth())
                            self.assertNotEqual(room.quarry.beams(room.earth_terrain)[index][1],receiver)
                            self.assertTrue(room.fits(x,beam_y,safe=True))
