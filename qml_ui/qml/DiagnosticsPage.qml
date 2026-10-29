pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

ColumnLayout {
    id: root
    required property var bridge
    required property var windowRef
    readonly property var controller: bridge.diagnosticController
    property bool reportVisible: false
    spacing: 12
    FileDialog { id: exportDialog; title: root.windowRef.tr("Экспортировать отчёт JSON"); fileMode: FileDialog.SaveFile; defaultSuffix: "json"; nameFilters: ["JSON (*.json)"]; onAccepted: root.controller.exportReport(selectedFile.toString()) }
    StyledText { text: root.windowRef.tr("Диагностика и компоненты"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 26; font.weight: Font.Bold }
    Flow {
        Layout.fillWidth: true; spacing: 8
        CutButton { text: root.windowRef.tr("Проверить компоненты"); enabled: !root.controller.busy; onClicked: root.controller.collect() }
        CutButton { text: root.windowRef.tr("Предпросмотр отчёта JSON"); selected: root.reportVisible; onClicked: root.reportVisible=!root.reportVisible }
        CutButton { text: root.windowRef.tr("Скопировать отчёт без личных данных"); onClicked: root.controller.copyReport() }
        CutButton { text: root.windowRef.tr("Экспортировать отчёт JSON"); enabled: !root.controller.busy; onClicked: exportDialog.open() }
    }
    ScrollView {
        id: scroll; Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: scroll.availableWidth; spacing: 10
            TextArea {
                visible: root.reportVisible; Layout.fillWidth: true; Layout.preferredHeight: 280
                implicitWidth: 300; implicitHeight: 280
                readOnly: true; text: root.controller.reportText; wrapMode: TextEdit.Wrap; selectByMouse: true
                color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; renderType: Text.QtRendering
                background: CutFrame { fillColor: Theme.background; lineColor: Theme.border; cut: Theme.cutSmall }
            }
            SectionHeader { indexText: "01"; title: root.windowRef.tr("Обнаруженное оборудование"); countText: root.controller.inventory.length.toString(); Layout.fillWidth: true }
            Repeater {
                model: root.controller.inventory
                delegate: ColumnLayout {
                    id: device
                    required property var modelData
                    Layout.fillWidth: true; spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: device.modelData.name; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 17; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        CutButton { text: root.windowRef.tr("Открыть"); onClicked: root.windowRef.openDevice(device.modelData.id) }
                        CutButton { visible: device.modelData.canProbe; text: root.windowRef.tr("Проверить настройки устройства"); enabled: !root.controller.busy; onClicked: root.controller.probeSolaar(device.modelData.id) }
                    }
                    StyledText { text: device.modelData.status+" · "+device.modelData.source; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    DisclosureItem { Layout.fillWidth: true; label: root.windowRef.tr("Расширенная диагностика"); text: device.modelData.details }
                }
            }
            SectionHeader { indexText: "02"; title: root.windowRef.tr("Компоненты и доступ"); countText: root.controller.components.length.toString(); Layout.fillWidth: true }
            Repeater {
                model: root.controller.components
                delegate: StyledText { required property var modelData; text: modelData.component+" · "+modelData.description; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
    }
    BusyIndicator { visible: root.controller.busy; running: visible; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
    StyledText { visible: root.controller.message.length>0; text: root.controller.message; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
}
