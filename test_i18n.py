import ast,re,unittest
from pathlib import Path
from i18n import EN,tr,set_language

class Translations(unittest.TestCase):
    def tearDown(self):set_language('ru')
    def test_every_russian_ui_literal_has_translation(self):
        tree=ast.parse(Path(__file__).with_name('app.py').read_text())
        missing=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.search('[А-Яа-я]',node.value):
                if node.value not in EN and node.value not in ['Русский','Язык / Language']:missing.append(node.value)
        self.assertEqual(missing,[])
    def test_switch_and_battery_suffix(self):
        set_language('en');self.assertEqual(tr('Применить'),'Apply')
        self.assertEqual(tr('99% · заряжается'),'99% · charging')
        set_language('ru');self.assertEqual(tr('Применить'),'Применить')
