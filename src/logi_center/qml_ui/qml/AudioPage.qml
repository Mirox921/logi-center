pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

ColumnLayout {
    id: root
    objectName: "audio-page"
    required property var bridge
    required property var windowRef
    readonly property var controller: bridge.audio
    property string section: "sound"
    onVisibleChanged: { if (!visible) controller.stopTest() }
    spacing: 10
    FileDialog { id: importer; title: root.windowRef.tr("Импортировать готовый эффект"); nameFilters: ["JSON (*.json)"]; onAccepted: root.controller.importPreset(selectedFile.toString()) }
    Flickable {
        Layout.fillWidth: true; Layout.preferredHeight: 38; contentHeight: height; contentWidth: tabs.implicitWidth; clip: true
        Row {
            id: tabs; spacing: 6
            Repeater {
                model: [{key:"sound",label:root.windowRef.tr("Звук")},{key:"microphone",label:root.windowRef.tr("Микрофон")},{key:"effects",label:root.windowRef.tr("Эквалайзер и эффекты")},{key:"test",label:root.windowRef.tr("Тест")},{key:"hardware",label:root.windowRef.tr("Дополнительно")}]
                delegate: CutButton { required property var modelData; text: modelData.label; selected: root.section === modelData.key; onClicked: { root.controller.stopTest(); root.section=modelData.key } }
            }
        }
    }
    ScrollView {
        id: scroll
        Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
        ColumnLayout {
            width: scroll.availableWidth
            spacing: 14
            AudioEndpoint { visible: root.section === "sound" || root.section === "microphone"; kind: root.section === "microphone" ? "source" : "sink"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            ColumnLayout {
                visible: root.section === "effects"; Layout.fillWidth: true; spacing: 12
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 760 ? 2 : 1
                    columnSpacing: 12; rowSpacing: 12
                    Repeater {
                        model: ["output","input"]
                        delegate: CutCard {
                            id: direction
                            required property string modelData
                            Layout.fillWidth: true; Layout.preferredWidth: 360
                            Layout.alignment: Qt.AlignTop
                            implicitHeight: presetContent.implicitHeight+24
                            inset: 12
                            ColumnLayout {
                                id: presetContent
                                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                spacing: 10
                                StyledText { text: direction.modelData === "output" ? root.windowRef.tr("Пресеты выхода") : root.windowRef.tr("Пресеты микрофона"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18; wrapMode: Text.Wrap; Layout.fillWidth: true }
                                StyledText {
                                    objectName: "preset-state-"+direction.modelData
                                    visible: root.controller.presetState !== "ready" || presets.count === 0
                                    text: root.controller.presetState === "loading" || root.controller.presetState === "idle" ? root.windowRef.tr("Загрузка пресетов…") : root.controller.presetState === "unavailable" ? root.windowRef.tr("EasyEffects не установлен. Для применения пресетов нужен EasyEffects.") : root.controller.presetState === "error" ? root.windowRef.tr("Не удалось прочитать пресеты. Проверь доступ к настройкам EasyEffects.") : root.windowRef.tr("Пресеты не установлены. Импортируй JSON или найди готовый пресет.")
                                    color: root.controller.presetState === "error" ? Theme.error : Theme.muted
                                    font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true
                                }
                                CutCombo { id: presets; visible: count>0; Layout.fillWidth: true; model: root.controller.presets[direction.modelData] || [] }
                                CutButton {
                                    objectName: "preset-apply-"+direction.modelData
                                    text: root.windowRef.tr("Применить")
                                    enabled: presets.count>0 && presets.currentIndex>=0 && presets.currentText.length>0 && root.controller.effectsAvailable && root.controller.presetState === "ready" && !root.controller.busy
                                    onClicked: root.controller.loadPreset(direction.modelData,presets.currentText)
                                }
                            }
                        }
                    }
                }
                StyledText { text: root.windowRef.tr("Пресеты изменяют программную обработку звука."); color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.Wrap }
                Flow {
                    Layout.fillWidth: true; spacing: 8
                    CutButton { text: root.windowRef.tr("Импортировать эффект"); enabled: !root.controller.busy && !root.bridge.simulationMode; onClicked: importer.open() }
                    CutButton { text: root.windowRef.tr("Открыть EasyEffects"); onClicked: root.bridge.launchTool("easyeffects") }
                    CutButton { text: root.windowRef.tr("Найти пресеты"); onClicked: root.bridge.launchTool("presets") }
                    CutButton { text: root.windowRef.tr("Включить эффекты"); enabled: root.controller.effectsAvailable && !root.controller.busy; onClicked: root.controller.setBypass(false) }
                    CutButton { text: root.windowRef.tr("Обойти эффекты"); enabled: root.controller.effectsAvailable && !root.controller.busy; onClicked: root.controller.setBypass(true) }
                }
            }
            ColumnLayout {
                visible: root.section === "test"; Layout.fillWidth: true; spacing: 12
                StyledText { text: root.windowRef.tr("Проверка микрофона"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 20 }
                CutCombo { Layout.fillWidth: true; model: root.controller.inputs; textRole: "label"; currentIndex: root.controller.inputs.findIndex(row=>row.name===root.controller.selectedInput.name); onActivated: index=>root.controller.selectEndpoint("source",root.controller.inputs[index].name) }
                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 14; color: Theme.background; border.color: Theme.border
                    Rectangle { width: parent.width*root.controller.level; height: parent.height; color: Theme.success }
                }
                Flow {
                    Layout.fillWidth: true; spacing: 8
                    CutButton { text: root.windowRef.tr("Показать уровень микрофона"); enabled: root.controller.captureAvailable && !root.controller.busy && root.controller.testState !== "recording"; onClicked: root.controller.startTest("meter") }
                    CutButton { text: root.windowRef.tr("Записать образец — до 8 секунд"); enabled: root.controller.captureAvailable && !root.controller.busy && root.controller.testState !== "recording"; onClicked: root.controller.startTest("record") }
                    CutButton { visible: ["preparing","meter","recording"].indexOf(root.controller.testState)>=0; text: root.windowRef.tr("Остановить тест"); onClicked: root.controller.stopTest() }
                    CutButton { visible: root.controller.clips.indexOf("original")>=0; text: root.windowRef.tr("Прослушать исходный"); onClicked: root.controller.play("original") }
                    CutButton { visible: root.controller.clips.indexOf("processed")>=0; text: root.windowRef.tr("Прослушать обработанный"); onClicked: root.controller.play("processed") }
                    CutButton { visible: root.controller.clips.length>0; text: root.windowRef.tr("Удалить временную запись"); onClicked: root.controller.stopTest() }
                }
                StyledText { text: root.windowRef.tr("Запись временная и удаляется при смене микрофона, отключении устройства или закрытии приложения. Обработанный образец появится только при подтверждённом маршруте EasyEffects от выбранного микрофона."); font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.subtle; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
            DeviceEditor { visible: root.section === "hardware" && root.bridge.selectedDevice.kind === "audio"; bridge: root.bridge; windowRef: root.windowRef; Layout.fillWidth: true; Layout.preferredHeight: 330 }
            StyledText { visible: root.section === "hardware" && root.bridge.selectedDevice.kind !== "audio"; text: root.windowRef.tr("Выбери гарнитуру на главной странице."); color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
    }
    BusyIndicator { visible: root.controller.busy; running: visible; Layout.preferredWidth: 28; Layout.preferredHeight: 28 }
    StyledText { visible: root.controller.message.length>0; text: root.controller.message; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
}
