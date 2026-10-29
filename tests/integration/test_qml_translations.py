"""Prevent mixed Russian/English labels in the optional presentation."""
from pathlib import Path
import re
import ast
import unittest
from logi_center.i18n import EN


class QmlTranslations(unittest.TestCase):
    def test_static_qml_russian_labels_have_actual_english_translations(self):
        missing=[]
        for path in (Path(__file__).resolve().parents[2]/'src/logi_center/qml_ui/qml').glob('*.qml'):
            for text in re.findall(r'\.tr\("([^"\n]+)"\)',path.read_text()):
                if not re.search('[А-Яа-яЁё]',text):continue
                if text not in EN or re.search('[А-Яа-яЁё]',EN[text]):missing.append((path.name,text))
        for name in ('src/logi_center/core/devices/device_presentation.py','src/logi_center/core/services/battery_presentation.py','src/logi_center/core/services/control_service.py','src/logi_center/adapters/mchose/k7_settings.py','src/logi_center/adapters/mchose/ace68_bindings.py','src/logi_center/qml_ui/bridge/editor.py','src/logi_center/qml_ui/bridge/audio.py','src/logi_center/qml_ui/bridge/diagnostics.py'):
            path=Path(__file__).resolve().parents[2]/name
            for node in ast.walk(ast.parse(path.read_text())):
                if not isinstance(node,ast.Constant) or not isinstance(node.value,str):continue
                text=node.value
                if re.search('[А-Яа-яЁё]',text) and (text not in EN or re.search('[А-Яа-яЁё]',EN[text])):
                    missing.append((name,text))
        self.assertEqual(missing,[])
