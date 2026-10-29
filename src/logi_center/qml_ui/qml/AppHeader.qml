import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Rectangle {
    id: header
    required property var bridge
    required property var windowRef
    color: Theme.surface1
    implicitHeight: 68
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }
    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 18; anchors.rightMargin: 18
        spacing: 12
        Image { source: Theme.assetRoot + "icons/logi-mark.svg"; Layout.preferredWidth: 40; Layout.preferredHeight: 40; sourceSize: Qt.size(80,80) }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            StyledText { text: "LOGI / CENTER"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: header.width < 800 ? 20 : 24; font.bold: true; font.letterSpacing: 0.5 }
            StyledText {
                Layout.fillWidth: true
                text: header.bridge.updatedAt ? header.windowRef.tr("%1 внешних · %2 встроенных · %3 аудио").arg(header.bridge.inventoryCounts.external || 0).arg(header.bridge.inventoryCounts.builtin || 0).arg(header.bridge.inventoryCounts.audio || 0) + ((header.bridge.inventoryCounts.other || 0) ? " · " + header.windowRef.tr("%1 других").arg(header.bridge.inventoryCounts.other) : "") + " · " + header.windowRef.tr("обновлено %1").arg(header.bridge.updatedAt) : header.windowRef.tr("Чтение устройств…")
                color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
        StatusLED { visible: header.bridge.simulationMode && header.width >= 1000; active: true; activeColor: Theme.warning; text: header.windowRef.tr("СИМ") }
        CutButton { visible: header.windowRef.page !== "dashboard"; text: "‹ " + header.windowRef.tr("Назад"); onClicked: header.windowRef.goBack(); implicitHeight: 38 }
        Row {
            spacing: 0
            Repeater {
                model: ["ru", "en"]
                delegate: CutButton {
                    id: languageButton
                    required property string modelData
                    objectName: "header-language-" + modelData
                    implicitWidth: 40; implicitHeight: 38
                    text: modelData.toUpperCase()
                    quietSelected: true
                    selected: header.bridge.language === modelData
                    contentItem: StyledText {
                        objectName: "header-language-label-" + languageButton.modelData
                        text: languageButton.text
                        color: languageButton.selected ? Theme.accent : Theme.text
                        font.family: Theme.dataFont; font.pixelSize: 12
                        font.bold: languageButton.selected
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    Accessible.name: modelData === "ru" ? "Русский" : "English"
                    onClicked: header.bridge.setLanguage(modelData)
                }
            }
        }
        CutButton {
            id: toolsButton
            objectName: "headerTools"
            text: header.width >= 1000 ? header.windowRef.tr("Инструменты") + " ≡" : "≡"
            implicitWidth: header.width >= 1000 ? 148 : 40
            implicitHeight: 38
            Accessible.name: header.windowRef.tr("Инструменты")
            ToolTip.visible: hovered; ToolTip.text: header.windowRef.tr("Настройки, резервные копии и диагностика")
            onClicked: tools.open()
            Menu {
                id: tools
                objectName: "headerToolsMenu"
                x: toolsButton.width - width; y: toolsButton.height + 5
                width: 260
                implicitHeight: 172
                padding: 6
                background: CutFrame { fillColor: Theme.surface2; lineColor: Theme.borderStrong; cut: Theme.cutSmall }
                Repeater {
                    model: [header.windowRef.tr("Настройки"), header.windowRef.tr("Резервные копии"), header.windowRef.tr("Диагностика"), header.windowRef.tr("О программе"), header.windowRef.tr("Звук")]
                    delegate: MenuItem {
                        id: menuEntry
                        required property int index
                        required property string modelData
                        text: modelData
                        implicitHeight: 40
                        background: Rectangle { color: menuEntry.highlighted ? Theme.surface4 : "transparent"; Rectangle { visible: menuEntry.activeFocus; anchors.left: parent.left; height: parent.height; width: 2; color: Theme.accent } }
                        contentItem: StyledText { text: menuEntry.text; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12; verticalAlignment: Text.AlignVCenter; leftPadding: 12 }
                        onTriggered: {
                            tools.close()
                            header.windowRef.openTools(index === 0 ? "settings" : index === 1 ? "backups" : index === 2 ? "diagnostics" : index === 3 ? "about" : "audio")
                        }
                    }
                }
            }
        }
    }
}
