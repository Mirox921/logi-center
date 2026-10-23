import tempfile,unittest
from pathlib import Path
from drafts import DraftStore
class Drafts(unittest.TestCase):
    def test_refresh_and_restart_retain_desired(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'drafts.json';store=DraftStore(path);store.edit('mouse/dpi',800,1600)
            self.assertEqual(DraftStore(path).get('mouse/dpi',800),(1600,False))
            self.assertEqual(path.stat().st_mode&0o777,0o600)
    def test_conflict_does_not_overwrite_draft(self):
        with tempfile.TemporaryDirectory() as root:
            store=DraftStore(Path(root)/'d');store.edit('button',['button','1'],['macro','KEY_A'])
            self.assertEqual(store.get('button',['button','2']),(['macro','KEY_A'],True))
            store.discard('button');self.assertEqual(store.get('button',3),(3,False))
    def test_corrupt_file(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'d';path.write_text('{')
            self.assertEqual(DraftStore(path).get('a',1),(1,False))

    def test_unverified_submission_keeps_desired_until_explicit_resolution(self):
        with tempfile.TemporaryDirectory() as root:
            store=DraftStore(Path(root)/'draft');store.edit('dpi',800,1600)
            store.submitted('dpi','sent_unverified')
            self.assertEqual(store.get('dpi',800),(1600,False))
            self.assertEqual(store.values['dpi']['submission_state'],'sent_unverified')
            store.submitted('dpi','confirmed');self.assertEqual(store.get('dpi',800),(800,False))
