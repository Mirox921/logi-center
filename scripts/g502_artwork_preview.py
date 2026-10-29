#!/usr/bin/env python3
"""Render the uninstalled G502 SVG candidate in Qt Quick, without device I/O."""
import json
import os
from pathlib import Path
import sys
import tempfile

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView, QQuickItem

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mouse_models import G502, editor_callouts


def render(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    buttons = [{'index': index, 'x': anchor[0] * 480, 'y': anchor[1] * 440,
                'cx': editor_callouts(11)[index][0] * 480,
                'cy': editor_callouts(11)[index][1] * 440}
               for index, anchor in sorted(G502.items())]
    qml = '''import QtQuick
Rectangle {
    width: 840; height: 462; color: "#1b1b19"
    property var buttons: BUTTONS
    Rectangle {
        x: 10; y: 12; width: 320; height: 240; color: "#121311"
        border.color: "#494943"
        Image {
            objectName: "dashboard-svg"
            anchors.centerIn: parent; width: 238; height: 218
            source: SOURCE; fillMode: Image.PreserveAspectFit; smooth: true
        }
    }
    Rectangle {
        x: 345; y: 12; width: 480; height: 440; color: "#121311"
        border.color: "#494943"
        Image {
            objectName: "editor-svg"
            anchors.fill: parent; source: SOURCE
            fillMode: Image.PreserveAspectFit; smooth: true
        }
        Canvas {
            anchors.fill: parent
            onPaint: {
                const b=parent.parent.buttons[3],ctx=getContext("2d")
                ctx.strokeStyle="#efa834";ctx.lineWidth=1.4
                ctx.beginPath();ctx.moveTo(b.cx+18,b.cy);ctx.lineTo(b.cx+31,b.cy)
                ctx.lineTo(b.x,b.y);ctx.stroke()
            }
        }
        Repeater {
            model: parent.parent.buttons
            delegate: Rectangle {
                required property var modelData
                x: modelData.x-3; y: modelData.y-3; width: 6; height: 6
                radius: 3; color: modelData.index===3 ? "#efa834" : "#a8aaa4"
            }
        }
        Repeater {
            model: parent.parent.buttons
            delegate: Rectangle {
                required property var modelData
                x: modelData.cx-17; y: modelData.cy-12; width: 34; height: 24
                color: "#242521"; border.color: modelData.index===3 ? "#efa834" : "#65655e"
                Text { anchors.centerIn: parent; text: String(modelData.index+1)
                       color: modelData.index===3 ? "#efa834" : "#d8d8d2"; font.pixelSize: 12 }
            }
        }
    }
}
'''.replace('BUTTONS', json.dumps(buttons, separators=(',', ':'))).replace('SOURCE', json.dumps(source.as_uri()))
    with tempfile.TemporaryDirectory() as temporary:
        qml_path = Path(temporary) / 'preview.qml'
        qml_path.write_text(qml, encoding='utf-8')
        app = QGuiApplication.instance() or QGuiApplication([])
        view = QQuickView()
        view.setSource(QUrl.fromLocalFile(str(qml_path)))
        if view.status() != QQuickView.Ready:
            raise RuntimeError('Qt Quick could not load the preview')
        view.show()

        errors = []

        def save():
            try:
                root = view.rootObject()
                for name in ('dashboard-svg', 'editor-svg'):
                    image = root.findChild(QQuickItem, name)
                    if image is None or float(image.property('implicitWidth') or 0) <= 0:
                        raise RuntimeError(f'Qt Quick did not decode {name}')
                output.parent.mkdir(parents=True, exist_ok=True)
                if not view.grabWindow().save(str(output)):
                    raise RuntimeError(f'Could not save {output}')
            except Exception as error:
                errors.append(error)
            finally:
                app.quit()

        QTimer.singleShot(300, save)
        app.exec()
        view.close()
        if errors:
            raise errors[0]
    return output


if __name__ == '__main__':
    project = Path(__file__).resolve().parents[1]
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else project / 'docs/artwork-proposals/g502-hero.svg'
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else project / 'docs/artwork-proposals/g502-hero-preview.png'
    print(render(source, output))
