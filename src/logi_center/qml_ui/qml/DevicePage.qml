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
    readonly property bool dockEditing: (bridge.editor.section === "dock" && bridge.editor.dockState.available === true) || bridge.editor.k7Editor || bridge.editor.aceEditor

    FileDialog {
        id: artworkDialog
        title: root.windowRef.tr("Выбери изображение устройства")
        fileMode: FileDialog.OpenFile
        nameFilters: ["Images (*.png *.webp *.svg)", "All files (*)"]
        onAccepted: root.bridge.previewUserArtwork(root.bridge.selectedDeviceId, selectedFile.toString())
    }

    Dialog {
        id: artworkPreview
        property string sourceUrl: ""
        property string failure: ""
        modal: true
        title: root.windowRef.tr("Предпросмотр изображения")
        standardButtons: Dialog.NoButton
        width: Math.min(520, root.width - 24)
        height: Math.min(430, root.height - 24)
        background: CutFrame { fillColor: Theme.surface2; lineColor: Theme.borderStrong; cut: Theme.cut }
        contentItem: ColumnLayout {
            spacing: 10
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
                CutFrame { anchors.fill: parent; fillColor: Theme.background; lineColor: Theme.border; cut: Theme.cutSmall }
                Image {
                    anchors.fill: parent
                    anchors.margins: 18
                    source: artworkPreview.sourceUrl
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: false
                }
            }
            StyledText {
                visible: artworkPreview.failure.length > 0
                text: artworkPreview.failure
                color: Theme.error
                font.family: Theme.dataFont
                font.pixelSize: 12
                wrapMode: Text.Wrap
                Layout.fillWidth: true
            }
        }
        footer: RowLayout {
            CutButton { text: root.windowRef.tr("ОТМЕНА"); implicitHeight: 34; onClicked: artworkPreview.close() }
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("ИСПОЛЬЗОВАТЬ"); primary: true; enabled: artworkPreview.sourceUrl.length > 0 && artworkPreview.failure.length === 0; implicitHeight: 34; onClicked: { root.bridge.setUserArtwork(root.bridge.selectedDeviceId, artworkPreview.sourceUrl); artworkPreview.close() } }
        }
    }

    Connections {
        target: root.bridge
        function onArtworkPreviewReady(deviceId, source, error) {
            if (deviceId !== root.bridge.selectedDeviceId) return
            artworkPreview.failure = error
            artworkPreview.sourceUrl = source
            artworkPreview.open()
        }
    }

    Dialog {
        id: nameDialog
        modal: true
        title: root.windowRef.tr("Имя устройства")
        standardButtons: Dialog.NoButton
        width: Math.min(440, root.width - 24)
        height: 190
        background: CutFrame { fillColor: Theme.surface2; lineColor: Theme.borderStrong; cut: Theme.cut }
        onOpened: deviceName.text = root.bridge.selectedDevice.name || ""
        contentItem: ColumnLayout {
            spacing: 12
            StyledText { text: root.windowRef.tr("Локальное имя для этого устройства"); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
            TextField {
            renderType: Text.QtRendering; font.hintingPreference: Theme.textHinting
                id: deviceName
                Layout.fillWidth: true
                implicitWidth: 300
                implicitHeight: 38
                color: Theme.text
                font.family: Theme.displayFont
                font.pixelSize: 13
                maximumLength: 48
                background: CutFrame { fillColor: Theme.background; lineColor: deviceName.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
            }
        }
        footer: RowLayout {
            CutButton { text: root.windowRef.tr("ОТМЕНА"); implicitHeight: 34; onClicked: nameDialog.close() }
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("СБРОСИТЬ"); implicitHeight: 34; onClicked: { root.bridge.setUserName(root.bridge.selectedDeviceId, ""); nameDialog.close() } }
            CutButton { text: root.windowRef.tr("СОХРАНИТЬ"); primary: true; implicitHeight: 34; onClicked: { root.bridge.setUserName(root.bridge.selectedDeviceId, deviceName.text); nameDialog.close() } }
        }
    }

    readonly property bool compactEditor: bridge.editor.eweadnEditor || bridge.editor.g515Editor || dockEditing || (bridge.editor.g502Editor && bridge.editor.section==="buttons")

    ColumnLayout {
        anchors.fill: parent
        spacing: 15

        CutCard {
            Layout.fillWidth: true
            Layout.preferredHeight: root.compactEditor ? 110 : root.width < 700 ? 248 : 206
            inset: 13
            RowLayout {
                anchors.fill: parent
                spacing: 18
                Item {
                    visible: !root.compactEditor
                    Layout.preferredWidth: Math.min(250, root.width * .34)
                    Layout.fillHeight: true
                    clip: true
                    CutFrame { anchors.fill: parent; fillColor: Theme.background; lineColor: Theme.border; cut: Theme.cutSmall }
                    DeviceImage {
                        anchors.centerIn: parent
                        readonly property var geometry: root.bridge.selectedDevice.artGeometry || ({valid:false,bounds:[0,0,1,1]})
                        readonly property var bounds: geometry.bounds
                        height: geometry.valid && !fallbackActive ? Math.min(parent.width * .88 / ((bounds[2]-bounds[0])*(geometry.aspect || 1.6)), parent.height*.86/(bounds[3]-bounds[1])) : parent.height*.87
                        width: geometry.valid && !fallbackActive ? height*(geometry.aspect || 1.6) : parent.width*.87
                        anchors.verticalCenterOffset: geometry.valid && !fallbackActive ? (.5-(bounds[1]+bounds[3])/2)*height : 0
                        requestedSource: root.bridge.selectedDevice.imageSource || ""
                        onFailed: function(source) { root.bridge.rejectArtwork(root.bridge.selectedDeviceId, source.toString()) }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    spacing: 7
                    StyledText {
                        text: root.bridge.selectedDevice.name || root.windowRef.tr("Устройство отключено")
                        color: Theme.text; font.family: Theme.displayFont; font.pixelSize: root.compactEditor ? 22 : 25; font.weight: Font.Bold
                        wrapMode: Text.Wrap; maximumLineCount: root.compactEditor ? 1 : 2; elide: Text.ElideRight; Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StatusLED { active: root.bridge.selectedDevice.connected === true; text: root.bridge.selectedDevice.connected === true ? root.windowRef.tr("Подключено") : root.windowRef.tr("Отключено") }
                        ConnectionTag { visible: (root.bridge.selectedDevice.connectionTag || "—") !== "—"; label: root.bridge.selectedDevice.connectionTag || "—" }
                        StyledText { visible: root.compactEditor && root.bridge.selectedDevice.showBattery === true; text: root.bridge.selectedDevice.batteryLabel || ""; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13 }
                        Item { Layout.fillWidth: true }
                    }
                    SegmentedBattery {
                        visible: !root.compactEditor && root.bridge.selectedDevice.showBattery === true
                        Layout.preferredWidth: Math.min(290, root.width * .46)
                        percent: root.bridge.selectedDevice.batteryPercent === undefined ? -1 : root.bridge.selectedDevice.batteryPercent
                        charging: root.bridge.selectedDevice.charging === true
                        label: root.bridge.selectedDevice.batteryLabel || root.windowRef.tr("Заряд: нет данных")
                    }
                    StyledText { visible: !root.compactEditor; text: root.bridge.selectedDevice.typeLabel || ""; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; font.letterSpacing: .7 }
                    RowLayout {
                        visible: !root.compactEditor
                        spacing: 7
                        CutButton { text: root.windowRef.tr("ИМЯ"); implicitHeight: 31; onClicked: nameDialog.open() }
                        CutButton { text: root.windowRef.tr("ИЗОБРАЖЕНИЕ"); implicitHeight: 31; enabled: root.bridge.selectedDevice.connected === true; onClicked: artworkDialog.open() }
                        CutButton { text: root.windowRef.tr("СБРОСИТЬ"); implicitHeight: 31; visible: root.bridge.selectedDevice.artworkSource === "user"; enabled: root.bridge.selectedDevice.connected === true; onClicked: root.bridge.clearUserArtwork(root.bridge.selectedDeviceId) }
                    }
                    StyledText { visible: root.bridge.error.length > 0; text: root.bridge.error; color: Theme.error; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
                }
            }
        }

        DisclosureItem {
            Layout.fillWidth: true
            label: root.windowRef.tr("Источники и изображение")
            text: root.windowRef.tr("Модуль управления") + ": " + (root.bridge.selectedDevice.sourceLabel || "—") + "\n"
                + (root.bridge.selectedDevice.artworkSourceLabel || "") + "\n"
                + root.windowRef.tr("Код изображения") + ": " + (root.bridge.selectedDevice.artworkSlug || "—") + "\n"
                + root.windowRef.tr("Файл изображения") + ": " + (root.bridge.selectedDevice.artworkFile || "—") + "\n"
                + "SHA-256: " + (root.bridge.selectedDevice.artworkHash || "—")
        }
        CutButton {
            visible: (root.bridge.selectedDevice.sourceLabel || "").indexOf("Solaar") >= 0 || (root.bridge.selectedDevice.name || "").indexOf("G515") >= 0
            text: root.windowRef.tr("Открыть Solaar")
            onClicked: root.bridge.launchTool("solaar")
        }

        DeviceEditor { visible: root.bridge.selectedDevice.kind !== "audio"; bridge: root.bridge; windowRef: root.windowRef; Layout.fillWidth: true; Layout.fillHeight: true; onChooseArtwork: artworkDialog.open() }
        AudioPage { visible: root.bridge.selectedDevice.kind === "audio"; bridge: root.bridge; windowRef: root.windowRef; Layout.fillWidth: true; Layout.fillHeight: true }
    }
}
