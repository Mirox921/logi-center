import unittest
from mouse_models import layout,linux_key,MacroDraft,conflicts
class MouseEditing(unittest.TestCase):
    def test_models_have_unique_button_areas(self):
        self.assertEqual(len(set(layout('G502 HERO',11).values())),11)
        self.assertEqual(len(layout('G305',6)),6)
        self.assertEqual(len(layout('unknown',9)),9)
    def test_capture_combination_and_repeat(self):
        draft=MacroDraft();draft.press('KEY_LEFTCTRL');draft.press('KEY_C');draft.press('KEY_C');draft.release('KEY_C');draft.release('KEY_LEFTCTRL');draft.validate()
        self.assertEqual(draft.tokens,['+KEY_LEFTCTRL','+KEY_C','-KEY_C','-KEY_LEFTCTRL'])
    def test_unreleased_key_rejected(self):
        draft=MacroDraft();draft.press('KEY_A')
        with self.assertRaises(ValueError):draft.validate()
    def test_key_mapping_and_desktop_warning(self):
        self.assertEqual(linux_key('Control_L'),'KEY_LEFTCTRL')
        self.assertIsNone(linux_key('unknown-key'))
        self.assertTrue(conflicts(['+KEY_LEFTALT','KEY_F4','-KEY_LEFTALT']))
