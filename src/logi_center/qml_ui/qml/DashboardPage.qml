pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Item {
    id: root
    required property var bridge
    required property var windowRef

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        DashboardToolbar { bridge: root.bridge; windowRef: root.windowRef; Layout.fillWidth: true; Layout.preferredHeight: 42 }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            // Render glyphs directly into the window; a viewport texture
            // resamples small labels at fractional display scales.
            Rectangle { anchors.fill: parent; color: Theme.background }
            Flickable {
                id: inventoryScroll
                objectName: "inventoryScroll"
                anchors.fill: parent
                anchors.rightMargin: 18
                clip: true
                pixelAligned: true
                contentWidth: width
                contentHeight: sectionsColumn.implicitHeight + 12
                boundsBehavior: Flickable.StopAtBounds
                visible: root.bridge.deviceModel.count > 0
                ScrollBar.vertical: ScrollBar { parent: inventoryScroll.parent; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 10; policy: ScrollBar.AsNeeded }
                Column {
                    id: sectionsColumn
                    y: 12
                    width: inventoryScroll.width
                    spacing: 22
                    DeviceSection { width: sectionsColumn.width; deviceModel: root.bridge.externalDeviceModel; windowRef: root.windowRef; indexText: "01"; title: "Внешняя периферия" }
                    DeviceSection { objectName: "builtinSection"; width: sectionsColumn.width; deviceModel: root.bridge.builtinDeviceModel; windowRef: root.windowRef; indexText: "02"; title: "Встроенные устройства" }
                    DeviceSection { objectName: "audioSection"; width: sectionsColumn.width; deviceModel: root.bridge.audioDeviceModel; windowRef: root.windowRef; indexText: "03"; title: "Аудио" }
                    DeviceSection { width: sectionsColumn.width; deviceModel: root.bridge.otherDeviceModel; windowRef: root.windowRef; indexText: "04"; title: "Другие устройства" }
                }
            }
            Rectangle {
                objectName: "panelFade"
                anchors.top: parent.top; width: parent.width; height: 12; z: 2
                gradient: Gradient { GradientStop { position: 0; color: Theme.background } GradientStop { position: 1; color: Qt.rgba(Theme.background.r,Theme.background.g,Theme.background.b,0) } }
            }
            EmptyState {
                anchors.fill: parent
                visible: root.bridge.deviceModel.count === 0 && !root.bridge.busy
                title: root.windowRef.tr(root.bridge.searchQuery ? "Ничего не найдено" : root.bridge.categoryFilter !== "all" ? "В этой категории нет устройств" : "Подключённые устройства появятся здесь")
                detail: root.windowRef.tr(root.bridge.searchQuery ? "Измени поиск или очисти фильтры." : "Подключи мышь, клавиатуру или аудиоустройство.")
                CutButton { visible: !!root.bridge.searchQuery; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 20; text: root.windowRef.tr("Очистить поиск"); onClicked: root.bridge.setSearch("") }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: root.bridge.error.length > 0 || root.bridge.busy
            StatusLED { active: root.bridge.busy; activeColor: Theme.warning; text: root.bridge.busy ? root.windowRef.tr("Поиск устройств") : root.bridge.error; visible: root.bridge.busy || root.bridge.error.length > 0 }
            Item { Layout.fillWidth: true }
            Rectangle { Layout.preferredWidth: 6; Layout.preferredHeight: 6; color: Theme.accent; visible: root.bridge.busy }
        }
    }
}
