"""Prevent mixed Russian/English labels in the optional presentation."""
from pathlib import Path
import re
import ast
import unittest
from i18n import EN


class QmlTranslations(unittest.TestCase):
    def test_static_qml_russian_labels_have_actual_english_translations(self):
        missing=[]
        for path in (Path(__file__).resolve().parent/'qml_ui/qml').glob('*.qml'):
            for text in re.findall(r'\.tr\("([^"\n]+)"\)',path.read_text()):
                if not re.search('[А-Яа-яЁё]',text):continue
                if text not in EN or re.search('[А-Яа-яЁё]',EN[text]):missing.append((path.name,text))
        for name in ('device_presentation.py','battery_presentation.py','control_service.py','k7_settings.py','ace68_bindings.py','qml_ui/bridge/editor.py','qml_ui/bridge/audio.py','qml_ui/bridge/diagnostics.py'):
            path=Path(__file__).resolve().parent/name
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node,ast.Constant) or not isinstance(node.value,str):continue
                text=node.value
                if re.search('[А-Яа-яЁё]',text) and (text not in EN or re.search('[А-Яа-яЁё]',EN[text])):
                    missing.append((name,text))
        self.assertEqual(missing,[])
