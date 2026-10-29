pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

CutCard {
    id: root
    required property var controller
    required property var windowRef
    property string metric: "actuation"
    property bool showValues: false
    property color previewColor: "transparent"
    readonly property var values: controller.aceKeyValues
    readonly property var selection: controller.aceSelectedKeys
    readonly property var keyColors: controller.aceKeyColors
    function colorFor(key) {
        const mode=controller.aceFields["mchose-ace68:lighting_mode"]
        const rgb=keyColors[key]
        return mode && mode.value==="Custom" && rgb ? Qt.rgba(rgb[0]/255,rgb[1]/255,rgb[2]/255,.65) : previewColor
    }
    Layout.fillWidth: true
    implicitHeight: board.boardHeight+58
    function caption(key) {
        const value=(values[key] || {})[metric]
        if (value===undefined || value===null) return "—"
        if (metric==="rapid_trigger") return value===0 ? "—" : "RT"
        return Number(value).toFixed(2)
    }
    ColumnLayout {
        anchors.fill: parent; spacing: 8
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: "ACE68 / 68"; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; Layout.fillWidth: true }
            StyledText { text: root.windowRef.tr("Выбрано клавиш")+": "+root.selection.length; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12 }
        }
        Item {
            id: board
            Layout.fillWidth: true; Layout.preferredHeight: boardHeight
            readonly property real unit: Math.min(width/16,42)
            readonly property real boardHeight: unit*4.6
            Item {
                id: keys
                anchors.horizontalCenter: parent.horizontalCenter
                width: board.unit*16; height: parent.height
                Repeater {
                    model: root.controller.keyModel
                    delegate: CutButton {
                        id: cap
                        required property var modelData
                        objectName: "ace-key-"+modelData.id
                        x: modelData.x*board.unit; y: modelData.y*board.unit*.92
                        width: modelData.w*board.unit-3; height: board.unit*.92-3
                        selected: root.selection.includes(modelData.id); quietSelected: true
                        enabled: !root.controller.busy
                        text: ({"Backspace":"⌫","Space":"Space","LShift":"⇧","RShift":"⇧","Enter":"↵","Caps":"⇪","Super":"◆","LCtrl":"Ctrl","RCtrl":"Ctrl","LAlt":"Alt","RAlt":"Alt","PgUp":"Pg↑","PgDn":"Pg↓"})[modelData.label] || modelData.label
                        contentItem: Item {
                            implicitHeight: root.showValues ? 28 : 14
                            Column {
                                anchors.centerIn: parent; spacing: 0; width: cap.width-4
                                StyledText { width: parent.width; text: cap.text; color: cap.selected ? Theme.accent : Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight }
                                StyledText { visible: root.showValues; width: parent.width; text: root.caption(cap.modelData.id); color: cap.selected ? Theme.accent : Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                            }
                        }
                        Rectangle { visible: !root.showValues; anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 4; height: 2; color: root.colorFor(cap.modelData.id) }
                        Accessible.name: modelData.label
                        ToolTip.visible: hovered; ToolTip.text: modelData.label+(root.showValues ? " · "+root.caption(modelData.id) : "")
                        onClicked: root.controller.toggleAceKey(modelData.id)
                    }
                }
            }
        }
    }
}
