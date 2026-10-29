pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    property string kind: "sink"
    readonly property var endpoints: kind === "sink" ? controller.outputs : controller.inputs
    readonly property var selected: kind === "sink" ? controller.selectedOutput : controller.selectedInput
    spacing: 12
    CutCombo {
        Layout.fillWidth: true
        model: root.endpoints
        textRole: "label"
        currentIndex: root.endpoints.findIndex(row => row.name === root.selected.name)
        enabled: !root.controller.busy
        onActivated: index => root.controller.selectEndpoint(root.kind,root.endpoints[index].name)
    }
    StyledText { visible: !!root.selected.route || !!root.selected.bus; text: [root.selected.bus || "",root.selected.route || ""].filter(part=>part.length>0).join(" · "); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.Wrap }
    RowLayout {
        Layout.fillWidth: true
        StyledText { text: root.selected.availability || root.windowRef.tr("Устройства не найдены"); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.Wrap }
        CutButton { text: root.selected.default ? root.windowRef.tr("Основное устройство") : root.windowRef.tr("Сделать основным"); enabled: root.selected.available === true && !root.selected.default && !root.controller.busy; onClicked: root.controller.applyEndpoint(root.kind,"default") }
    }
    StyledText { text: root.kind === "sink" ? root.windowRef.tr("Уровень громкости") : root.windowRef.tr("Уровень микрофона"); font.family: Theme.displayFont; font.pixelSize: 19; color: Theme.text }
    RowLayout {
        Layout.fillWidth: true
        CutSlider { Layout.fillWidth: true; from: 0; to: 100; stepSize: 1; value: root.selected.desiredVolume || 0; enabled: root.selected.available === true && root.selected.volume !== null && !root.controller.busy; onMoved: root.controller.editVolume(root.kind,Math.round(value)) }
        StyledText { text: root.selected.desiredVolume === null || root.selected.desiredVolume === undefined ? "—" : root.selected.desiredVolume+"%"; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 22 }
    }
    StyledText { visible: root.selected.conflict === true; text: root.windowRef.tr("Конфликт черновика"); color: Theme.error; font.family: Theme.dataFont; font.pixelSize: 13 }
    Flow {
        Layout.fillWidth: true; spacing: 8
        CutButton { text: root.selected.mute ? root.windowRef.tr("Включить звук") : root.windowRef.tr("Выключить звук"); enabled: typeof root.selected.mute === "boolean" && root.selected.available === true && !root.controller.busy; onClicked: root.controller.applyEndpoint(root.kind,"mute") }
        CutButton { visible: root.selected.dirty === true; text: root.windowRef.tr("Отменить черновик"); onClicked: root.controller.discardVolume(root.kind) }
        CutButton { visible: root.selected.dirty === true; text: root.windowRef.tr("Применить"); primary: true; enabled: !root.selected.conflict && !root.controller.busy; onClicked: root.controller.applyEndpoint(root.kind,"volume") }
    }
}
