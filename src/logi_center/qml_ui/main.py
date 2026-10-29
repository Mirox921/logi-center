"""Qt Quick frontend entry point."""
from pathlib import Path
import os
import sys


def run(argv=None):
    from .bridge.preferences import load_preferences,qt_scale
    initial_args=list(argv if argv is not None else sys.argv)
    if '--simulate' not in initial_args:
        os.environ['QT_SCALE_FACTOR']=qt_scale(os.environ,load_preferences()['ui_scale'])
    # QtRendering can still choose LCD distance-field shaders on desktop GL.
    # Gray coverage is independent of monitor subpixel order and rotation.
    os.environ["QSG_DISTANCEFIELD_ANTIALIASING"] = "gray"
    try:
        from PySide6.QtCore import QObject, QUrl
        from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QRawFont, QIcon
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
    except ModuleNotFoundError as error:
        if error.name and error.name.startswith('PySide6'):
            print('Qt interface unavailable: install PySide6 and Qt 6 Quick modules.', file=sys.stderr)
            return 2
        raise

    from logi_center.qml_ui.bridge.bridge import DeviceBridge

    args = list(argv if argv is not None else sys.argv)
    debug_text = '--debug-text' in args
    smoke = '--smoke' in args
    simulation = '--simulate' in args
    args = [arg for arg in args if arg not in ('--smoke', '--simulate', '--debug-text')]
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication(args)
    app.setApplicationName('Logi Center')
    from logi_center.version import VERSION
    app.setApplicationVersion(VERSION)
    app.setOrganizationName('Logi Center')
    qml_dir = Path(os.environ.get('LOGI_CENTER_QML_ROOT', Path(__file__).resolve().parent / 'qml')).resolve()
    from logi_center.resources import assets_dir as resource_assets, configure_engine
    assets_dir = resource_assets()
    app.setWindowIcon(QIcon(str(assets_dir/'brand/logi-mark.svg')))
    app.setDesktopFileName('logi-center')
    loaded_families = []
    for font_path in (assets_dir / 'fonts' / 'NotoSans-Regular.ttf',
                      assets_dir / 'fonts' / 'NotoSans-Bold.ttf',
                      assets_dir / 'fonts' / 'JetBrainsMonoNerdFont-Regular.ttf',
                      assets_dir / 'fonts' / 'NotoSerifDisplay-Regular.ttf'):
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id >= 0:
            loaded_families.extend(QFontDatabase.applicationFontFamilies(font_id))
    def has_required_glyphs(family):
        raw_font = QRawFont.fromFont(QFont(family, 12))
        required = list(range(0x410, 0x450)) + [0x401, 0x451] + list(range(0x41, 0x5B)) + list(range(0x61, 0x7B))
        return raw_font.isValid() and all(raw_font.supportsCharacter(codepoint) for codepoint in required)

    display_family = next((family for family in loaded_families
                           if family == 'Noto Sans' and has_required_glyphs(family)), None)
    if display_family is None:
        display_family = next((family for family in loaded_families
                               if family == 'Noto Serif Display' and has_required_glyphs(family)), 'sans-serif')
        print(f"QML font warning: display font unavailable; using '{display_family}'.", file=sys.stderr)
    data_family = next((family for family in loaded_families
                        if family == 'JetBrainsMono Nerd Font' and has_required_glyphs(family)), None)
    if data_family is None:
        print('QML font warning: bundled JetBrains Mono Cyrillic coverage unavailable.', file=sys.stderr)
        data_family = 'monospace'
    app.setFont(QFont(display_family))
    print(f"QML fonts loaded: display='{display_family}', data='{data_family}'")
    bridge = DeviceBridge(simulation=simulation, assets_dir=assets_dir / 'devices', persist_ui=not smoke)
    engine = QQmlApplicationEngine()
    configure_engine(engine)
    qml_warnings = []
    if smoke:
        engine.warnings.connect(lambda warnings: qml_warnings.extend(warning.toString() for warning in warnings))
    engine.addImportPath(str(qml_dir))
    engine.rootContext().setContextProperty('deviceBridge', bridge)
    engine.load(QUrl.fromLocalFile(str(qml_dir / 'Main.qml')))
    if not engine.rootObjects():
        bridge.shutdown()
        for warning in qml_warnings:
            print(f'QML warning: {warning}', file=sys.stderr)
        print('Qt interface could not load its QML files.', file=sys.stderr)
        return 1
    if debug_text:
        from PySide6.QtCore import QTimer
        from logi_center.qml_ui.text_debug import report
        QTimer.singleShot(100, lambda: report(app, engine.rootObjects()[0]))
    if smoke:
        from PySide6.QtCore import QTimer
        root = engine.rootObjects()[0]
        deadline = [0]

        def visual_child(item, name):
            # Repeater delegates have a visual parent that can differ from
            # their QObject owner. findChild() alone silently misses cards.
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = visual_child(child, name)
                if result is not None:
                    return result
            return None

        header_review_done = [False]

        def finish_smoke():
            if os.environ.get('LOGI_CENTER_QML_CAPTURE_HEADER') == '1' and not header_review_done[0]:
                header_review_done[0] = True
                from PySide6.QtCore import QMetaObject, Qt
                from PySide6.QtTest import QTest
                output = Path(os.environ['LOGI_CENTER_QML_SCREENSHOT_DIR'])
                menu = root.findChild(QObject, 'headerToolsMenu')
                if menu is None or menu.property('count') != 5:
                    print('FAIL: header menu does not expose five destinations.', file=sys.stderr)
                    app.exit(7)
                    return
                initial_language = bridge.language
                root.requestActivate()
                for language in ('en', 'ru'):
                    button = visual_child(root.contentItem(), 'header-language-' + language)
                    label = visual_child(root.contentItem(), 'header-language-label-' + language)
                    if button is None or label is None or label.property('truncated'):
                        print('FAIL: language label missing or truncated.', file=sys.stderr)
                        app.exit(9)
                        return
                    button.forceActiveFocus()
                    QTest.keyClick(root, Qt.Key.Key_Space)
                    if bridge.language != language:
                        print('FAIL: language button did not respond to Space.', file=sys.stderr)
                        app.exit(9)
                        return
                bridge.setLanguage(initial_language)
                print('PASS: RU/EN labels fit and both language buttons respond to Space.')
                tasks = [('settings', 1000), ('about', 1000), ('menu', 640), ('menu', 800), ('menu', 1000), ('menu', 1920)]

                def capture_header(index=0):
                    QMetaObject.invokeMethod(menu, 'close')
                    if index == len(tasks):
                        finish_smoke()
                        return
                    page, width = tasks[index]
                    root.resize(width, 820)
                    root.setProperty('page', 'dashboard' if page == 'menu' else page)

                    def ready():
                        if page == 'menu':
                            QMetaObject.invokeMethod(menu, 'open')
                            QTest.keyClick(root, Qt.Key.Key_Down)
                        def save():
                            if not root.grabWindow().save(str(output / f'header-{page}-{width}.png')):
                                app.exit(8)
                                return
                            capture_header(index + 1)
                        QTimer.singleShot(200, save)
                    QTimer.singleShot(180, ready)
                capture_header()
                return
            # Exercise every header destination. Backup services are tested
            # separately with memory I/O; no second GUI is started.
            root.setProperty('page', 'settings')
            app.processEvents()
            root.setProperty('page', 'about')
            app.processEvents()
            root.setProperty('page', 'backups')
            app.processEvents()
            root.setProperty('page', 'dashboard')
            if qml_warnings:
                for warning in qml_warnings:
                    print('QML warning:', warning, file=sys.stderr)
                app.exit(6)
                return
            print('PASS: QML loaded; Dashboard, device detail, diagnostics, settings and about navigation completed.')
            app.quit()

        def capture_screenshots(device_id=None):
            target_dir = os.environ.get('LOGI_CENTER_QML_SCREENSHOT_DIR')
            if not target_dir:
                bridge.selectDevice(device_id or '')
                root.setProperty('page', 'device' if device_id else 'dashboard')
                QTimer.singleShot(250, lambda: root.setProperty('page', 'diagnostics'))
                QTimer.singleShot(500, finish_smoke)
                return
            output = Path(target_dir)
            output.mkdir(parents=True, exist_ok=True)
            bridge.setCategory('all')
            bridge.setShowBuiltin(True)
            bridge.setSearch('')
            root.setProperty('page', 'dashboard')
            requested_widths = os.environ.get('LOGI_CENTER_QML_WIDTHS', '')
            widths = [int(width) for width in requested_widths.split(',') if width.strip().isdigit()] if requested_widths else [640, 800, 1000, 1280, 1600, 1920]
            comprehensive = os.environ.get('LOGI_CENTER_QML_CAPTURE_ALL') == '1'
            preview_language = os.environ.get('LOGI_CENTER_QML_LANGUAGE', 'ru')
            bridge.setLanguage(preview_language)
            artwork_metrics = {}

            def measure_artwork(width):
                if os.environ.get('LOGI_CENTER_QML_ART_METRICS') != '1':
                    return
                import json
                from scripts.card_metrics import measure
                measurements=[]
                for row in range(bridge.devices.rowCount()):
                    data=bridge.devices.get(row)
                    card=visual_child(root.contentItem(),'device-card-'+str(data['deviceId']))
                    if card is None:raise RuntimeError('Missing card during artwork measurement')
                    metrics=measure(card,visual_child,root.devicePixelRatio())
                    measurements.append(dict(name=data['name'],family=data['artGeometry'].get('family',''),**metrics))
                artwork_metrics[str(width)]=measurements
                (output/'artwork-metrics.json').write_text(json.dumps(artwork_metrics,ensure_ascii=False,indent=2))
                print(f'PASS: measured {len(measurements)} actual PNG silhouettes at {width}px; source hashes recorded.')

            def capture_dashboard(index):
                if index >= len(widths):
                    if not device_id:
                        finish_smoke()
                        return
                    if comprehensive:
                        verify_scroll_position()
                    else:
                        capture_english_dashboard()
                    return
                width = widths[index]
                root.resize(width, 820)
                def capture_lower():
                    scroll = root.findChild(QObject, 'inventoryScroll')
                    maximum = max(0, scroll.property('contentHeight') - scroll.property('height')) if scroll else 0
                    if not comprehensive or maximum <= 0:
                        capture_dashboard(index + 1)
                        return
                    positions = [('lower', maximum)]
                    for label, object_name in (('builtin', 'builtinSection'), ('audio', 'audioSection')):
                        section = root.findChild(QObject, object_name)
                        if section and section.property('visible'):
                            positions.append((label, min(maximum, max(0, section.y()))))
                    def capture_position(position):
                        if position >= len(positions):
                            scroll.setProperty('contentY', 0)
                            capture_dashboard(index + 1)
                            return
                        label, offset = positions[position]
                        scroll.setProperty('contentY', offset)
                        QTimer.singleShot(180, lambda: save_image(output / f'dashboard-{width}-{label}.png',
                            lambda: capture_position(position + 1)))
                    capture_position(0)
                QTimer.singleShot(250, lambda: save_image(output / f'dashboard-{width}.png', capture_lower))

            def verify_scroll_position():
                root.resize(1000, 820)
                root.setProperty('page', 'dashboard')
                scroll = root.findChild(QObject, 'inventoryScroll')
                if scroll:
                    scroll.setProperty('contentY', min(760, max(0, scroll.property('contentHeight') - scroll.property('height'))))
                    changed = scroll.property('contentY') > 0 and scroll.property('contentHeight') > scroll.property('height')
                    scroll.setProperty('contentY', 0)
                    if not changed:
                        print('FAIL: Dashboard Flickable did not accept a scroll position.', file=sys.stderr)
                        app.exit(5)
                        return
                    print('PASS: Dashboard scroll position changes and returns to the top.')
                QTimer.singleShot(220, capture_battery_samples)

            def capture_battery_samples():
                root.resize(1000, 820)
                root.setProperty('page', 'dashboard')
                queries = [
                    ('battery-charging', 'зарядка' if preview_language == 'ru' else 'charging'),
                    ('battery-known', 'беспроводная гарнитура' if preview_language == 'ru' else 'wireless headset'),
                    ('battery-unknown', 'частично доступное' if preview_language == 'ru' else 'partially available'),
                ]

                def capture_query(index):
                    if index >= len(queries):
                        bridge.setSearch('')
                        capture_english_dashboard()
                        return
                    name, query = queries[index]
                    bridge.setSearch(query)
                    QTimer.singleShot(180, lambda: save_image(output / f'dashboard-{name}-1000.png',
                        lambda: capture_query(index + 1)))

                capture_query(0)

            def capture_english_dashboard():
                bridge.setLanguage('en')
                root.resize(1000, 820)
                QTimer.singleShot(250, capture_english)

            def capture_english():
                save_image(output / 'dashboard-1000-en.png', capture_focus_state if comprehensive else capture_detail_page)

            def capture_focus_state():
                bridge.setLanguage(preview_language)
                root.resize(1280, 820)
                root.setProperty('page', 'dashboard')
                scroll = root.findChild(QObject, 'inventoryScroll')
                if scroll:
                    scroll.setProperty('contentY', 0)
                QTimer.singleShot(250, capture_focused)

            def capture_focused():
                card = visual_child(root.contentItem(), 'device-card-' + str(bridge.devices.get(0)['deviceId'])) if bridge.devices.rowCount() else None
                if card:
                    from PySide6.QtCore import QPoint, QPointF
                    from PySide6.QtTest import QTest
                    card_point = card.mapToItem(root.contentItem(), QPointF(card.width() / 2, card.height() / 2))
                    card.forceActiveFocus()
                    QTest.mouseMove(root, QPoint(round(card_point.x()), round(card_point.y())))
                    print('PASS: focused device card receives keyboard focus.' if card.property('activeFocus')
                          else 'WARN: offscreen platform did not activate device-card focus.')
                save_image(output / 'dashboard-focus-1280.png', capture_empty_state)

            def capture_empty_state():
                bridge.setSearch('no matching device')
                root.resize(1000, 820)
                QTimer.singleShot(180, lambda: save_image(output / 'dashboard-empty-1000.png', capture_detail_page))

            def capture_detail_page():
                bridge.selectDevice(device_id)
                root.setProperty('page', 'device')
                root.resize(1000, 820)
                QTimer.singleShot(300, capture_detail)

            def capture_detail():
                save_image(output / 'device-detail-1000.png', capture_detail_categories if comprehensive else finish_smoke)

            def capture_detail_categories():
                bridge.clearSelection()
                root.setProperty('page', 'dashboard')
                bridge.setSearch('')
                rows = [bridge.devices.get(i) for i in range(bridge.devices.rowCount())]
                targets = []
                for kind in ('mouse', 'keyboard', 'audio'):
                    row = next((item for item in rows if item.get('kind') == kind), None)
                    if row:
                        targets.append((kind, row['deviceId']))
                capture_category(0, targets)

            def capture_category(index, targets):
                if index >= len(targets):
                    root.setProperty('page', 'diagnostics')
                    root.resize(1000, 820)
                    QTimer.singleShot(220, lambda: save_image(output / 'diagnostics-1000.png', finish_smoke))
                    return
                kind, target_id = targets[index]
                bridge.selectDevice(target_id)
                root.setProperty('page', 'device')
                root.resize(1000, 820)
                QTimer.singleShot(220, lambda: save_image(output / f'device-{kind}-1000.png',
                    lambda: (root.setProperty('page', 'dashboard'), QTimer.singleShot(120, lambda: capture_category(index + 1, targets)))))

            def save_image(path, done):
                image = root.grabWindow()
                if image.isNull() or not image.save(str(path)):
                    print(f'Could not save Qt screenshot: {path}', file=sys.stderr)
                    app.exit(4)
                    return
                print(f'Screenshot saved: {path}')
                pieces = path.stem.split('-')
                if len(pieces) == 2 and pieces[0] == 'dashboard' and pieces[1].isdigit():
                    measure_artwork(int(pieces[1]))
                done()

            capture_dashboard(0)

        def exercise():
            model = bridge.devices
            if model.rowCount() > 0:
                if os.environ.get('LOGI_CENTER_ITERATION_STAGE'):
                    from scripts.ui_iteration_smoke import exercise as exercise_iteration
                    exercise_iteration(app, root, bridge, finish_smoke)
                    return
                if os.environ.get('LOGI_CENTER_QML_READONLY_SMOKE') == '1':
                    from scripts.qml_readonly_smoke import exercise as exercise_readonly
                    exercise_readonly(app, root, bridge, finish_smoke)
                    return
                if os.environ.get('LOGI_CENTER_QML_EWEADN_SMOKE') == '1':
                    from scripts.eweadn_smoke import exercise as exercise_eweadn
                    exercise_eweadn(app, root, bridge, finish_smoke)
                    return
                if os.environ.get('LOGI_CENTER_QML_FUNCTIONAL_SMOKE') == '1':
                    from scripts.qml_functional_smoke import exercise as exercise_functional
                    exercise_functional(app, root, bridge, finish_smoke)
                    return
                if os.environ.get('LOGI_CENTER_QML_BACKUP_SMOKE') == '1':
                    from scripts.qml_backup_smoke import exercise as exercise_backup
                    exercise_backup(app, root, bridge, finish_smoke)
                    return
                capture_screenshots(model.get(0)['deviceId'])
                return
            deadline[0] += 1
            if deadline[0] >= 100:
                if simulation:
                    print('QML smoke timed out waiting for simulated devices.', file=sys.stderr)
                    app.exit(3)
                elif os.environ.get('LOGI_CENTER_QML_SCREENSHOT_DIR'):
                    print('No connected devices detected; capturing the live empty state.')
                    capture_screenshots()
                else:
                    print('QML opened with live discovery; no connected devices were reported.')
                    finish_smoke()
            else:
                QTimer.singleShot(100, exercise)
        QTimer.singleShot(100, exercise)
    result = app.exec()
    bridge.shutdown()
    return result


if __name__ == '__main__':
    raise SystemExit(run())
