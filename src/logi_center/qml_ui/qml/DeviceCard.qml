pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ItemDelegate {
    id: card
    required property var deviceData
    required property var windowRef
    signal open(string deviceId)
    objectName: "device-card-" + deviceData.deviceId
    hoverEnabled: true
    padding: 0
    implicitHeight: 406
    Accessible.name: deviceData.name + ", " + deviceData.typeLabel + ", " + deviceData.status
    Accessible.role: Accessible.Button
    onClicked: open(deviceData.deviceId)
    Keys.onReturnPressed: open(deviceData.deviceId)
    Keys.onEnterPressed: open(deviceData.deviceId)
    Keys.onSpacePressed: open(deviceData.deviceId)
    background: CutFrame {
        fillColor: card.down ? Theme.surface3 : card.hovered ? Theme.surface2 : Theme.surface1
        lineColor: card.activeFocus || card.hovered ? Theme.accent : Theme.border
        lineWidth: card.activeFocus ? 2 : 1
        cut: Theme.cut
        Behavior on fillColor { ColorAnimation { duration: Theme.motion } }
    }
    ToolTip.visible: hovered && nameText.truncated
    ToolTip.text: deviceData.name
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 6
        ColumnLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 58; Layout.minimumHeight: 58; Layout.maximumHeight: 58
            spacing: 2
            RowLayout {
                Layout.fillWidth: true
                StyledText {
                    id: nameText
                    Layout.fillWidth: true
                    text: card.deviceData.name
                    color: card.deviceData.readOnly ? Theme.muted : Theme.text
                    font.family: Theme.displayFont; font.pixelSize: 17; font.bold: true
                    elide: Text.ElideRight
                }
                Rectangle {
                    width: 7; height: 7
                    color: card.deviceData.connected ? Theme.success : Theme.warning
                    Accessible.name: card.deviceData.status
                }
            }
            RowLayout {
                Layout.fillWidth: true
                StyledText { Layout.fillWidth: true; text: card.deviceData.typeLabel; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 13; elide: Text.ElideRight }
                ConnectionTag { visible: !!card.deviceData.connectionTag && card.deviceData.connectionTag !== "—"; label: card.deviceData.connectionTag || ""; implicitHeight: 28; tone: Theme.muted }
            }
        }
        Item {
            id: stage
            Layout.fillWidth: true; Layout.preferredHeight: 240; Layout.minimumHeight: 240; Layout.maximumHeight: 240
            readonly property var geometry: card.deviceData.artGeometry || ({valid:false,bounds:[.1,.1,.9,.9],shadow_bounds:[.1,.1,.9,.9]})
            readonly property var bounds: artwork.fallbackActive ? [.1,.1,.9,.9] : geometry.bounds
            readonly property var fullBounds: geometry.shadow_bounds || bounds
            readonly property bool measured: geometry.valid && !artwork.fallbackActive
            readonly property real bodyWidth: bounds[2]-bounds[0]
            readonly property real bodyHeight: bounds[3]-bounds[1]
            readonly property real artAspect: geometry.aspect || 1.6
            readonly property bool mouseFamily: measured && geometry.family === "mouse"
            readonly property bool keyboardFamily: measured && geometry.family === "keyboard"
            readonly property real targetHeight: mouseFamily ? scene.height*.8/bodyHeight : keyboardFamily ? scene.width*.85/bodyWidth/artAspect : scene.height*.80/bodyHeight
            readonly property real canvasHeight: !measured ? scene.height*.82 : Math.min(targetHeight,scene.height*.832/(fullBounds[3]-fullBounds[1]),scene.width*(keyboardFamily ? .94 : .748)/(fullBounds[2]-fullBounds[0])/artAspect)
            Item {
                id: scene
                objectName: "deviceScene"
                height: 240
                width: 320
                anchors.horizontalCenter: parent.horizontalCenter
                clip: true
                CutFrame { anchors.fill: parent; fillColor: Theme.background; lineColor: Theme.border; lineWidth: .7; cut: Theme.cutSmall }
                Repeater {
                    model: 9
                    delegate: Rectangle { required property int index; x: scene.width * (index + 1) / 10; y: 10; width: 1; height: scene.height-20; color: Theme.border; opacity: .13 }
                }
                Repeater {
                    model: 4
                    delegate: Rectangle { required property int index; y: scene.height * (index + 1) / 5; x: 10; width: scene.width-20; height: 1; color: Theme.border; opacity: .10 }
                }
                Rectangle { x: 8; y: 8; width: card.hovered ? 19 : 13; height: 1; color: card.activeFocus || card.hovered ? Theme.accent : Theme.borderStrong; opacity: .4 }
                Rectangle { x: 8; y: 8; width: 1; height: card.hovered ? 19 : 13; color: card.activeFocus || card.hovered ? Theme.accent : Theme.borderStrong; opacity: .4 }
                Rectangle { x: scene.width-22; y: scene.height-9; width: 14; height: 1; color: card.activeFocus || card.hovered ? Theme.accent : Theme.borderStrong; opacity: .4 }
                DeviceImage {
                    id: artwork
                    objectName: "deviceArtwork"
                    anchors.centerIn: parent
                    anchors.verticalCenterOffset: stage.measured ? (.5-(stage.fullBounds[1]+stage.fullBounds[3])/2)*height : 0
                    readonly property real hoverShift: stage.measured && (stage.geometry.family === "touchpad" || stage.geometry.family === "pointer_generic") ? Math.min(3,Math.max(0,scene.width*.38-(stage.fullBounds[2]-stage.fullBounds[0])*width/2-.5)) : 3
                    anchors.horizontalCenterOffset: (card.hovered ? hoverShift : 0) + (stage.measured ? (.5-(stage.fullBounds[0]+stage.fullBounds[2])/2)*width : 0)
                    height: stage.canvasHeight
                    width: stage.measured ? height * stage.artAspect : scene.width * .94
                    requestedSource: card.deviceData.imageSource
                    onFailed: function(source) { card.windowRef.bridge.rejectArtwork(card.deviceData.deviceId, source.toString()) }
                    opacity: card.deviceData.readOnly ? .72 : 1
                    Behavior on anchors.horizontalCenterOffset { NumberAnimation { duration: Theme.motion; easing.type: Easing.OutCubic } }
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 44; Layout.minimumHeight: 44; Layout.maximumHeight: 44
            spacing: 1
            SegmentedBattery {
                objectName: "cardBattery"
                visible: card.deviceData.showBattery === true
                Layout.fillWidth: true
                percent: card.deviceData.batteryPercent
                charging: card.deviceData.charging
                label: card.deviceData.batteryPercent < 0 && card.deviceData.batteryState === "unknown" ? card.windowRef.tr("Заряд: нет данных") : card.deviceData.batteryLabel || card.windowRef.tr("Нет данных")
            }
            StyledText { text: card.deviceData.showBattery && card.deviceData.charging ? card.windowRef.tr("Заряжается") : ""; color: Theme.charging; font.family: Theme.dataFont; font.pixelSize: 12; Layout.alignment: Qt.AlignRight }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 22
            spacing: 8
            StyledText { text: card.deviceData.settingsLabel; color: card.deviceData.availableSettings > 0 ? Theme.muted : Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 13 }
            Item { Layout.fillWidth: true }
            StyledText { visible: !card.deviceData.showSource && card.deviceData.generalizedArtwork; text: card.deviceData.artworkNote; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; elide: Text.ElideRight; Layout.maximumWidth: card.width * .46 }
            StyledText { visible: card.deviceData.showSource; text: card.deviceData.sourceLabel; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; elide: Text.ElideRight; Layout.maximumWidth: card.width * .44 }
            StyledText { text: "→"; color: card.activeFocus || card.hovered ? Theme.accent : Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 14 }
        }
    }
}
