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
    readonly property var dock: controller.dockState
    readonly property bool wide: width >= 820
    readonly property bool colored: ["static", "breathing", "flash", "stars"].includes(root.dock.mode)
    function rgbColor() {
        const rgb = root.dock.color || [0, 0, 0]
        return Qt.rgba(rgb[0]/255, rgb[1]/255, rgb[2]/255, 1)
    }
    ColorDialog {
        id: colorPicker
        title: root.windowRef.tr("Выбери цвет подсветки")
        selectedColor: root.rgbColor()
        onAccepted: root.controller.edit("mchose:dock:color", [Math.round(selectedColor.r*255), Math.round(selectedColor.g*255), Math.round(selectedColor.b*255)])
    }
    EmptyState {
        visible: !root.dock.available
        Layout.fillWidth: true; Layout.preferredHeight: 130
        title: root.windowRef.tr("Подсветка дока не прочитана")
        detail: root.windowRef.tr("Разбуди K7 Ultra и нажми «Прочитать настройки».")
    }
    GridLayout {
        visible: root.dock.available
        Layout.fillWidth: true
        columns: root.wide ? 2 : 1
        columnSpacing: 14; rowSpacing: 14
        CutCard {
            Layout.row: root.wide ? 0 : 1; Layout.column: 0
            Layout.fillWidth: !root.wide; Layout.fillHeight: root.wide
            Layout.preferredWidth: 290; Layout.preferredHeight: root.wide ? 430 : 230
            ColumnLayout {
                anchors.fill: parent; spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    StyledText { text: root.windowRef.tr("Подсветка"); font.family: Theme.displayFont; font.pixelSize: 16; color: Theme.text; Layout.fillWidth: true }
                    CutButton {
                        objectName: "dock-enabled"
                        visible: root.wide
                        text: root.dock.enabled ? root.windowRef.tr("Включено") : root.windowRef.tr("Выключено")
                        selected: !!root.dock.enabled; quietSelected: true
                        enabled: root.dock.writable
                        onClicked: root.controller.edit("mchose:dock:enabled", !root.dock.enabled)
                    }
                }
                Item {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    Item {
                        id: artwork
                        anchors.centerIn: parent
                        height: Math.min(parent.height, parent.width*400/262)
                        width: height*262/400
                        Image { anchors.fill: parent; source: "../assets/diagrams/k7-dock.svg"; sourceSize: Qt.size(524,800); fillMode: Image.PreserveAspectFit }
                        Canvas {
                            id: strip
                            anchors.fill: parent
                            onWidthChanged: requestPaint()
                            onHeightChanged: requestPaint()
                            Connections { target: root.controller; function onChanged() { strip.requestPaint() } }
                            onPaint: {
                                const ctx=getContext("2d"); ctx.reset()
                                const s=width/262, x=20*s, y=16*s, w=224*s, h=370*s, r=49*s
                                ctx.beginPath(); ctx.moveTo(x+r,y); ctx.lineTo(x+w-r,y)
                                ctx.quadraticCurveTo(x+w,y,x+w,y+r); ctx.lineTo(x+w,y+h-r)
                                ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h); ctx.lineTo(x+r,y+h)
                                ctx.quadraticCurveTo(x,y+h,x,y+h-r); ctx.lineTo(x,y+r)
                                ctx.quadraticCurveTo(x,y,x+r,y); ctx.closePath()
                                let tint=root.colored ? root.rgbColor() : Theme.muted
                                if (root.dock.mode === "battery" && root.dock.enabled) {
                                    tint=ctx.createLinearGradient(0,y+h,0,y)
                                    tint.addColorStop(0,Theme.error); tint.addColorStop(.5,Theme.accent); tint.addColorStop(1,Theme.success)
                                }
                                ctx.strokeStyle=root.dock.enabled ? tint : Theme.borderStrong
                                ctx.globalAlpha=root.dock.enabled ? (root.dock.brightness || 0)/100 : .5
                                ctx.lineWidth=4*s; ctx.stroke()
                            }
                        }
                        StyledText {
                            anchors.horizontalCenter: parent.horizontalCenter; y: parent.height*.38
                            text: "8K / RX"; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: Math.max(11,parent.width*.047)
                        }
                    }
                }
                StyledText { text: root.windowRef.tr("Предпросмотр"); color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; Layout.alignment: Qt.AlignHCenter }
            }
        }
        ColumnLayout {
            Layout.row: 0; Layout.column: root.wide ? 1 : 0
            Layout.fillWidth: true; Layout.alignment: Qt.AlignTop
            spacing: 14
            CutCard {
                Layout.fillWidth: true; Layout.preferredHeight: effects.implicitHeight+32
                ColumnLayout {
                    id: effects
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.windowRef.tr("Эффекты подсветки"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16; Layout.fillWidth: true }
                        CutButton {
                            objectName: "dock-enabled"
                            visible: !root.wide
                            text: root.dock.enabled ? root.windowRef.tr("Включено") : root.windowRef.tr("Выключено")
                            selected: !!root.dock.enabled; quietSelected: true; enabled: root.dock.writable
                            onClicked: root.controller.edit("mchose:dock:enabled", !root.dock.enabled)
                        }
                    }
                    GridLayout {
                        Layout.fillWidth: true; columns: width >= 570 ? 3 : 2; columnSpacing: 7; rowSpacing: 7
                        Repeater {
                            model: root.controller.dockModes
                            delegate: CutButton {
                                required property var modelData
                                objectName: "dock-mode-"+modelData.value
                                Layout.fillWidth: true
                                text: modelData.label; selected: root.dock.mode === modelData.value; quietSelected: true
                                enabled: root.dock.writable && !!root.dock.enabled
                                onClicked: root.controller.edit("mchose:dock:mode", modelData.value)
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: root.windowRef.tr("Яркость"); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13 }
                        CutSlider {
                            objectName: "dock-brightness"
                            Layout.fillWidth: true
                            from: 0; to: 100; stepSize: 1; value: root.dock.brightness || 0
                            enabled: root.dock.writable && !!root.dock.enabled
                            onMoved: root.controller.edit("mchose:dock:brightness", Math.round(value))
                            Accessible.name: root.windowRef.tr("Яркость док-станции")
                        }
                        StyledText { text: (root.dock.brightness === null ? "—" : root.dock.brightness)+"%"; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 14; Layout.preferredWidth: 43 }
                    }
                    RowLayout {
                        visible: root.dock.mode === "flash" || root.dock.mode === "stars"
                        Layout.fillWidth: true
                        StyledText { text: root.windowRef.tr("Длительность"); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13 }
                        CutCombo {
                            Layout.fillWidth: true
                            model: [root.windowRef.tr("Короткая"), root.windowRef.tr("Средняя"), root.windowRef.tr("Долгая")]
                            currentIndex: typeof root.dock.duration === "number" ? root.dock.duration : -1
                            enabled: root.dock.writable && !!root.dock.enabled
                            onActivated: index => root.controller.edit("mchose:dock:duration", index)
                        }
                    }
                    RowLayout {
                        visible: root.dock.mode === "wave"; Layout.fillWidth: true
                        StyledText { text: root.windowRef.tr("Направление"); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13 }
                        CutCombo {
                            Layout.fillWidth: true
                            model: [root.windowRef.tr("По часовой стрелке"), root.windowRef.tr("Против часовой стрелки")]
                            currentIndex: typeof root.dock.direction === "number" ? root.dock.direction : -1
                            enabled: root.dock.writable && !!root.dock.enabled
                            onActivated: index => root.controller.edit("mchose:dock:direction", index)
                        }
                    }
                }
            }
            CutCard {
                Layout.fillWidth: true; Layout.preferredHeight: palette.implicitHeight+32
                ColumnLayout {
                    id: palette
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    spacing: 12
                    StyledText { text: root.dock.mode === "battery" ? root.windowRef.tr("Уровень заряда") : root.colored ? root.windowRef.tr("Цвет") : root.windowRef.tr("Аппаратный эффект"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16 }
                    Rectangle {
                        visible: root.dock.mode === "battery"
                        Layout.fillWidth: true; Layout.preferredHeight: 12
                        gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: Theme.error } GradientStop { position: .5; color: Theme.accent } GradientStop { position: 1; color: Theme.success } }
                    }
                    RowLayout {
                        visible: root.dock.mode === "battery"; Layout.fillWidth: true
                        StyledText { text: "0%"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                        Item { Layout.fillWidth: true }
                        StyledText { text: "100%"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                    }
                    RowLayout {
                        visible: root.colored
                        CutButton { objectName: "dock-color-picker"; text: root.windowRef.tr("Выбрать цвет"); enabled: root.dock.writable && !!root.dock.enabled; onClicked: colorPicker.open() }
                        Rectangle { Layout.preferredWidth: 48; Layout.preferredHeight: 32; color: root.rgbColor(); border.color: Theme.borderStrong }
                        StyledText { text: String(root.rgbColor()).toUpperCase(); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13 }
                    }
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: root.dock.mode === "battery" ? root.windowRef.tr("Цвет выбирает док-станция по заряду мыши. Пороги не изменяются.") : root.windowRef.tr("Эффект выполняет док-станция. Свечение и анимация программой не считываются.")
                        color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12
                    }
                }
            }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Изменения отправляются только кнопкой «Применить». Музыкальный режим недоступен.")
                color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12
            }
        }
    }
}
