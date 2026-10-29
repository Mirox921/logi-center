pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    readonly property bool freestyle: controller.section === "freestyle"
    readonly property var presets: ["#ffffff","#f3aa32","#ed5151","#66bc85","#58b8d4","#8e83d4"]
    property color paintColor: "#f3aa32"
    spacing: 12
    function paint(color) {
        paintColor=color
        controller.paintG515([Math.round(paintColor.r*255),Math.round(paintColor.g*255),Math.round(paintColor.b*255)])
    }
    ColorDialog {
        id: picker
        title: root.windowRef.tr("Выбери цвет подсветки")
        selectedColor: root.paintColor
        onAccepted: root.paint(selectedColor)
    }
    CutCard {
        Layout.fillWidth: true
        implicitHeight: preview.implicitHeight+28
        ColumnLayout {
            id: preview
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                StyledText { text: "G515 · LIGHTSYNC"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18; Layout.fillWidth: true }
                StyledText { text: "ANSI / TKL"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
            }
            Item {
                id: keyboard
                objectName: "g515-keyboard"
                Layout.fillWidth: true
                Layout.preferredHeight: pitch*6.5
                readonly property real pitch: Math.min(width/18.5,54)
                Repeater {
                    model: root.controller.g515KeyModel
                    delegate: Rectangle {
                        id: key
                        required property var capability
                        readonly property var modelData: capability
                        x: Math.round((keyboard.width-keyboard.pitch*18.5)/2+modelData.x*keyboard.pitch)
                        y: Math.round(modelData.y*keyboard.pitch)
                        width: Math.max(4,Math.round(modelData.w*keyboard.pitch)-3)
                        height: Math.max(4,Math.round(modelData.h*keyboard.pitch)-3)
                        color: modelData.selected ? Theme.accentSoft : Theme.surface2
                        border.color: modelData.selected || activeFocus ? Theme.accent : modelData.dirty ? Theme.warning : Theme.border
                        border.width: modelData.selected ? 2 : 1
                        radius: 2
                        activeFocusOnTab: hit.enabled
                        Keys.onPressed: event => {
                            if (hit.enabled && (event.key === Qt.Key_Space || event.key === Qt.Key_Return)) {
                                root.controller.selectG515Key(modelData.id,!!(event.modifiers & (Qt.ControlModifier|Qt.ShiftModifier)))
                                event.accepted=true
                            }
                        }
                        StyledText {
                            anchors.centerIn: parent
                            text: ({Print:"Prt",Scroll:"Scr",Pause:"Pau",Insert:"Ins"})[key.modelData.label] || key.modelData.label
                            font.family: Theme.dataFont
                            font.pixelSize: Math.max(8,Math.min(12,keyboard.pitch/3.4))
                            color: key.modelData.selected ? Theme.accent : Theme.text
                        }
                        Rectangle {
                            visible: !!key.modelData.color
                            anchors.bottom: parent.bottom; anchors.bottomMargin: 3
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: Math.max(3,parent.width*0.45); height: 2
                            color: key.modelData.color || "transparent"
                        }
                        MouseArea {
                            id: hit
                            objectName: "g515-key-"+key.modelData.id
                            anchors.fill: parent
                            enabled: root.freestyle && key.modelData.available && !root.controller.busy
                            hoverEnabled: true
                            cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: mouse => root.controller.selectG515Key(key.modelData.id,!!(mouse.modifiers & (Qt.ControlModifier|Qt.ShiftModifier)))
                        }
                        ToolTip.visible: hit.containsMouse
                        ToolTip.text: key.modelData.label+" · LED "+key.modelData.id
                        ToolTip.delay: 400
                        Accessible.role: Accessible.Button
                        Accessible.name: key.modelData.label
                        Accessible.onPressAction: if (hit.enabled) root.controller.selectG515Key(key.modelData.id,false)
                    }
                }
            }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Схема ANSI. Цвета — локальная конфигурация Solaar, не показания светодиодов.")
                font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.muted
            }
        }
    }
    ColumnLayout {
        visible: root.freestyle
        Layout.fillWidth: true
        spacing: 10
        StyledText { text: root.windowRef.tr("Быстрый выбор клавиш"); font.family: Theme.displayFont; font.pixelSize: 16; color: Theme.text }
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: implicitHeight
            spacing: 6
            Repeater {
                model: [{id:"wasd",label:"WASD"},{id:"numbers",label:root.windowRef.tr("Цифры")},{id:"function",label:"F1–F12"},
                        {id:"modifiers",label:root.windowRef.tr("Модификаторы")},{id:"arrows",label:root.windowRef.tr("Стрелки")},
                        {id:"all",label:root.windowRef.tr("Все клавиши")},{id:"none",label:root.windowRef.tr("Снять выделение")}]
                delegate: CutButton {
                    required property var modelData
                    text: modelData.label
                    enabled: root.controller.available && !root.controller.busy
                    onClicked: root.controller.selectG515Group(modelData.id)
                }
            }
        }
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: implicitHeight
            spacing: 7
            Repeater {
                model: root.presets
                delegate: Rectangle {
                    id: swatch
                    required property string modelData
                    objectName: "g515-paint-"+modelData
                    width: 32; height: 32; radius: 3; color: modelData
                    border.color: activeFocus ? Theme.accent : Theme.borderStrong
                    activeFocusOnTab: paintHit.enabled
                    Accessible.role: Accessible.Button
                    Accessible.name: modelData
                    Accessible.onPressAction: if (paintHit.enabled) root.paint(modelData)
                    Keys.onPressed: event => {
                        if (paintHit.enabled && (event.key===Qt.Key_Return || event.key===Qt.Key_Space)) {
                            root.paint(modelData); event.accepted=true
                        }
                    }
                    MouseArea { id: paintHit; anchors.fill: parent; enabled: root.controller.g515SelectionCount>0 && !root.controller.busy; onClicked: root.paint(swatch.modelData) }
                }
            }
            CutButton { text: root.windowRef.tr("Выбрать цвет"); enabled: root.controller.g515SelectionCount>0 && !root.controller.busy; onClicked: picker.open() }
        }
        StyledText {
            text: root.windowRef.tr("Выбрано клавиш: ")+root.controller.g515SelectionCount+" · Ctrl / Shift: "+root.windowRef.tr("Множественный выбор")
            font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
            Layout.fillWidth: true; wrapMode: Text.Wrap
        }
        Flow {
            Layout.fillWidth: true; Layout.preferredHeight: implicitHeight
            spacing: 9
            Repeater {
                model: root.controller.g515Palette
                delegate: Row {
                    required property var modelData
                    spacing: 5
                    Rectangle { width: 14; height: 14; color: parent.modelData.color; border.color: Theme.borderStrong }
                    StyledText { text: parent.modelData.count; font.family: Theme.dataFont; font.pixelSize: 12; color: Theme.muted }
                }
            }
        }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Применить включает управление RGB и статичный эффект, затем отправляет цвета выбранных клавиш. Изменения остальных клавиш сохраняются. Аппаратное считывание цветов недоступно.")
            font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.muted
        }
        StyledText {
            visible: root.controller.g515Palette.length===0
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Нет сохранённой карты LED. Сначала настрой поклавишную подсветку в Solaar; неизвестные зоны не записываются.")
            font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.warning
        }
    }
    GridLayout {
        visible: root.controller.section === "lighting" || root.controller.section === "keyboard_settings"
        Layout.fillWidth: true
        columns: width>=760 ? 2 : 1
        columnSpacing: 10; rowSpacing: 10
        Repeater {
            model: root.controller.g515Editor ? root.controller.fieldModel : []
            delegate: ControlEditor {
                required property var capability
                field: capability; controller: root.controller; windowRef: root.windowRef
                Layout.fillWidth: true; Layout.preferredWidth: 340; Layout.alignment: Qt.AlignTop
            }
        }
    }
    StyledText {
        visible: ["lighting","keyboard_settings"].includes(root.controller.section) && root.controller.fieldModel.count===0
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.controller.busy ? root.windowRef.tr("Выполняется…") : root.windowRef.tr("Настройки Solaar недоступны. Проверь подключение G515 и сохранённую конфигурацию Solaar.")
        font.family: Theme.displayFont; font.pixelSize: 14; color: Theme.warning
    }
    StyledText {
        visible: root.controller.section === "lighting"
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Статичный цвет, дыхание, цикл цветов и выключение передаются штатному эффекту Solaar. Меньший период — быстрее. Доступность проверяется backend при применении; автономность G515 после выхода не подтверждена.")
        font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.muted
    }
    CutCard {
        visible: root.controller.section === "animations" || root.controller.section === "assignments" || root.controller.section === "keyboard_settings"
        Layout.fillWidth: true
        implicitHeight: info.implicitHeight+28
        ColumnLayout {
            id: info
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 10
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.controller.section==="animations" ? root.windowRef.tr("Анимации G HUB") : root.controller.section==="assignments" ? "BASE / FN / G-SHIFT" : root.windowRef.tr("Память и питание")
                color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 17
            }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.controller.section==="animations" ? root.windowRef.tr("Contrast · Lightning · Ocean Wave · Red White Blue · Verticool. Это каталог из референса G HUB; воспроизведение, редактор кадров, экранные и аудиоэффекты пока не реализованы. Штатные эффекты находятся в разделе подсветки.") :
                      root.controller.section==="assignments" ? root.windowRef.tr("Backend G515 пока не предоставляет проверенного переназначения BASE/FN/G-SHIFT, действий при нажатии/удержании/отпускании и аппаратных макросов. LED-зоны не являются кодами назначения клавиш. Изменение этих функций недоступно.") :
                      root.windowRef.tr("Эти таймеры относятся к подсветке, а не к переходу всей клавиатуры в сон. Автономность, слоты встроенной памяти, стартовые эффекты и сброс не подтверждены backend; они не изменяются. Настройки Solaar локальные, батарея показывается в заголовке по доступным данным устройства.")
                color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14
            }
        }
    }
}
