pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

Item {
    id: root
    required property var bridge
    required property var windowRef
    readonly property var controller: bridge.backups
    FileDialog {
        id: openDialog
        objectName: "backupOpenDialog"
        title: root.windowRef.tr("Открыть резервную копию")
        nameFilters: ["JSON (*.json)"]
        onAccepted: root.controller.inspectFile(selectedFile.toString())
    }
    FileDialog {
        id: saveDialog
        objectName: "backupSaveDialog"
        title: root.windowRef.tr("Сохранить настройки устройства")
        fileMode: FileDialog.SaveFile
        defaultSuffix: "json"
        nameFilters: ["JSON (*.json)"]
        onAccepted: root.controller.exportFile(selectedFile.toString())
    }
    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        SectionHeader { Layout.fillWidth: true; indexText: "04"; title: root.windowRef.tr("Резервные копии"); countText: root.controller.selectedCount.toString() }
        StyledText {
            visible: root.bridge.simulationMode
            Layout.fillWidth: true
            text: root.windowRef.tr("Симуляция: аппаратные настройки не изменены.")
            color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap
        }
        ComboBox {
            id: targetBox
            implicitHeight: 40
            implicitWidth: 320
            objectName: "backupTarget"
            Layout.fillWidth: true
            enabled: !root.controller.busy
            model: root.controller.targets
            textRole: "name"
            valueRole: "key"
            currentIndex: {
                for (let i = 0; i < model.length; i++) if (model[i].key === root.controller.selectedKey) return i
                return -1
            }
            onActivated: root.controller.selectTarget(currentValue)
            font.family: Theme.displayFont; font.pixelSize: 14
            background: CutFrame { fillColor: Theme.surface1; lineColor: targetBox.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
            contentItem: StyledText { text: targetBox.displayText; color: Theme.text; font: targetBox.font; verticalAlignment: Text.AlignVCenter; leftPadding: 12; rightPadding: 32; elide: Text.ElideRight }
            indicator: StyledText { text: "⌄"; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 20; x: targetBox.width - 28; y: 5 }
            delegate: ItemDelegate {
                id: option
                required property var modelData
                required property int index
                width: targetBox.width - 12; height: 36
                highlighted: targetBox.highlightedIndex === index
                contentItem: StyledText { text: option.modelData.name; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                background: Rectangle { color: option.highlighted ? Theme.surface4 : Theme.surface2 }
            }
            popup: Popup {
                objectName: "backupTargetPopup"
                focus: true
                y: targetBox.height + 4
                width: targetBox.width
                implicitHeight: Math.min(220, options.contentHeight + 12)
                padding: 6
                background: CutFrame { fillColor: Theme.surface2; lineColor: Theme.borderStrong; cut: Theme.cutSmall }
                contentItem: ListView { id: options; clip: true; model: targetBox.delegateModel; currentIndex: targetBox.highlightedIndex; ScrollBar.vertical: ScrollBar {} }
            }
        }
        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: childrenRect.height
            spacing: 8
            CutButton { text: root.windowRef.tr("Экспортировать"); enabled: root.controller.targetAvailable && !root.controller.busy; onClicked: saveDialog.open() }
            CutButton { text: root.windowRef.tr("Открыть копию"); primary: true; enabled: root.controller.targetAvailable && !root.controller.busy; onClicked: openDialog.open() }
        }
        RowLayout {
            Layout.fillWidth: true
            BusyIndicator { visible: root.controller.busy; running: visible && Theme.motion > 0; implicitWidth: 24; implicitHeight: 24 }
            StyledText { Layout.fillWidth: true; text: root.controller.message; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
            CutButton { visible: root.controller.busy; text: root.windowRef.tr("Остановить"); onClicked: root.controller.cancel() }
        }
        StyledText { visible: !!root.controller.targetNote; Layout.fillWidth: true; text: root.controller.targetNote; color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
        EmptyState {
            visible: !root.controller.targets.length
            Layout.fillWidth: true
            title: root.windowRef.tr("Нет доступных настроек для резервного копирования")
            detail: root.windowRef.tr("Проверь подключение и доступность backend.")
        }
        ListView {
            id: fields
            objectName: "backupFields"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: root.controller.fieldModel
            ScrollBar.vertical: ScrollBar { }
            delegate: CutFrame {
                id: row
                required property var field
                width: fields.width - 12
                height: content.implicitHeight + 24
                fillColor: Theme.surface1; lineColor: Theme.border; cut: Theme.cutSmall
                ColumnLayout {
                    id: content
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    anchors.margins: 12; spacing: 6
                    CheckBox {
                        objectName: "backup-field-" + row.field.id
                        Layout.fillWidth: true
                        text: row.field.label
                        checked: row.field.selected
                        enabled: !root.controller.busy && !row.field.result
                        onToggled: root.controller.fieldModel.select(row.field.id, checked)
                        font.family: Theme.displayFont; font.pixelSize: 14
                        contentItem: StyledText { text: parent.text; leftPadding: 30; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.WordWrap }
                        indicator: CutFrame { x: 0; y: 3; width: 20; height: 20; cut: 4; fillColor: parent.checked ? Theme.accentSoft : Theme.background; lineColor: parent.activeFocus ? Theme.accent : Theme.borderStrong
                            StyledText { anchors.centerIn: parent; text: row.field.selected ? "✓" : ""; color: Theme.accent; font.family: Theme.dataFont; font.pixelSize: 13 }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.preferredWidth: 1; spacing: 3
                            StyledText { text: root.windowRef.tr(root.controller.reportAvailable ? "До восстановления" : "Сейчас"); color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                            StyledText { Layout.fillWidth: true; text: row.field.current; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                            StyledText { Layout.fillWidth: true; text: row.field.currentSource; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                        StyledText { text: "→"; color: Theme.accent; font.family: Theme.dataFont; font.pixelSize: 18 }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.preferredWidth: 1; spacing: 3
                            StyledText { text: root.windowRef.tr("Из копии"); color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                            StyledText { Layout.fillWidth: true; text: row.field.desired; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
                            StyledText { Layout.fillWidth: true; text: row.field.backupSource; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                    }
                    StyledText { visible: !!row.field.result; Layout.fillWidth: true; text: row.field.result; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
                    StyledText { visible: !!row.field.actual; Layout.fillWidth: true; text: root.windowRef.tr("Получено:") + " " + (row.field.actual || "") + " · " + (row.field.resultSource || ""); color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap }
                }
            }
        }
        DisclosureItem {
            visible: root.controller.skipped.length > 0 || !!root.controller.safetyPath
            Layout.fillWidth: true
            label: root.windowRef.tr("Пропущенные поля и технические подробности")
            text: root.controller.skipped.join("\n") + (root.controller.safetyPath ? "\n" + root.windowRef.tr("Защитная копия:") + " " + root.controller.safetyPath : "")
        }
        CutButton {
            objectName: "backupRestore"
            Layout.alignment: Qt.AlignRight
            primary: true
            text: root.windowRef.tr("Восстановить выбранное") + " · " + root.controller.selectedCount
            enabled: root.controller.canRestore
            onClicked: root.controller.restoreSelected()
        }
    }
}
