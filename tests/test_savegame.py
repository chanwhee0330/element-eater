"""실제 임시 JSON 파일로 새 게임·이어하기의 저장과 복원을 검사한다."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from src.room import Room
from src.savegame import SaveStore, restore
from src.combat import Projectile


class SavegameTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'continue.json'
        self.store = SaveStore(self.path)

    def test_missing_file_has_no_continue(self):
        self.assertIsNone(self.store.load())
        self.assertFalse(self.path.exists())

    def test_progress_health_enemies_and_projectiles_round_trip(self):
        room = Room()
        room.player.x, room.player.y, room.player.hp = 10, 14, 73
        room.aggro, room.elapsed = True, 8.5
        room.damage(room.enemies[0], 5, (1, 0))
        room.enemies[1].active = False
        room.enemies[1].hp = 0
        room.start_attack(room.player)
        room.player.attack_elapsed = .2
        room.projectiles.append(Projectile(10, 13, 0, -1, 'hero', 7, 3, 5, .1))
        self.store.write(room)
        record = self.store.load()
        self.assertEqual(record['stage'], 1)
        restored = Room()
        restore(record, restored)
        self.assertEqual(asdict(restored.player), asdict(room.player))
        self.assertEqual([asdict(e) for e in restored.enemies], [asdict(e) for e in room.enemies])
        self.assertEqual([asdict(s) for s in restored.projectiles], [asdict(s) for s in room.projectiles])
        self.assertEqual(restored.safe, room.safe)
        self.assertEqual(restored.elapsed, room.elapsed)
        self.assertTrue(restored.aggro)

    def test_new_game_replaces_previous_progress(self):
        room = Room()
        room.player.hp = 20
        self.store.write(room)
        room.reset()
        self.store.write(room)
        restored = Room()
        restore(self.store.load(), restored)
        self.assertEqual(restored.player.hp, 100)
        self.assertEqual(restored.remaining_enemies, 4)
        self.assertEqual(restored.player.y, 19.5)

    def test_death_does_not_overwrite_last_live_checkpoint(self):
        room = Room()
        room.player.hp = 50
        self.store.write(room)
        room.damage(room.player, 50)
        self.store.write(room)
        self.assertEqual(self.store.load()['state']['player']['hp'], 50)

    def test_clear_removes_continue(self):
        self.store.write(Room())
        self.store.clear()
        self.assertIsNone(self.store.load())

    def test_corrupt_or_incompatible_save_is_disabled_without_deleting_it(self):
        for payload in ('{broken', 'null', '{"version": 999}', '{"version": 1, "stage": 2}'):
            self.path.write_text(payload, encoding='utf-8')
            self.assertIsNone(self.store.load())
            self.assertEqual(self.path.read_text(encoding='utf-8'), payload)

    def test_invalid_health_position_and_nonfinite_data_are_disabled(self):
        for key, value in (('hp', -1), ('hp', 101), ('x', 100), ('y', float('nan')), ('active', 1), ('facing', 'invalid')):
            self.store.write(Room())
            record = json.loads(self.path.read_text(encoding='utf-8'))
            record['state']['player'][key] = value
            self.path.write_text(json.dumps(record), encoding='utf-8')
            self.assertIsNone(self.store.load())

    def test_save_is_atomic_and_leaves_no_temporary_file(self):
        self.store.write(Room())
        self.assertIsNotNone(self.store.load())
        self.assertFalse(self.path.with_suffix('.tmp').exists())


if __name__ == '__main__':
    unittest.main()
