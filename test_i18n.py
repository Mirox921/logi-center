import ast,re,unittest
from pathlib import Path
from i18n import EN,tr,set_language

class Translations(unittest.TestCase):
    def tearDown(self):set_language('ru')
    def test_every_russian_ui_literal_has_translation(self):
        trees=[ast.parse(Path(__file__).with_name(name).read_text()) for name in ['app.py','mouse_editor.py','microphone_ui.py','diagnostics.py']]
        tree=ast.Module(body=[node for tree in trees for node in tree.body],type_ignores=[])
        missing=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.search('[А-Яа-я]',node.value):
                if node.value not in EN and node.value not in ['Русский','Язык / Language']:missing.append(node.value)
        self.assertEqual(missing,[])
    def test_switch_and_battery_suffix(self):
        set_language('en');self.assertEqual(tr('Применить'),'Apply')
        self.assertEqual(tr('99% · заряжается'),'99% · charging')
        set_language('ru');self.assertEqual(tr('Применить'),'Применить')
