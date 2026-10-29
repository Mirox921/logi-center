pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import Theme 1.0

ApplicationWindow {
    id: root
    objectName: "macro-recorder-window"
    required property var controller
    required property var windowRef
    transientParent: windowRef
    modality: Qt.ApplicationModal
    title: windowRef.tr("Библиотека макросов")
    width: Math.min(880,windowRef.width); height: Math.min(740,windowRef.height)
    minimumWidth: 620; minimumHeight: 600
    color: Theme.background
    property int delay: 100
    onClosing: controller.stopRecording()
    onVisibleChanged: { if (!visible) controller.stopRecording() }
    onActiveChanged: { if (!active && visible) controller.stopRecording() }
    Connections {
        target: root.controller
        function onChanged() {
            if (!root.controller.available || (root.controller.section!=="buttons" && !(root.controller.eweadnEditor && root.controller.section==="macros"))) { root.controller.stopRecording(); root.hide() }
            if (!name.activeFocus) name.text=root.controller.libraryMacroName
        }
    }
    ColumnLayout {
        parent: root.contentItem
        anchors.fill: parent; anchors.margins: 16; spacing: 10
        StyledText {
            visible: !root.controller.macroLibraryAvailable
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Библиотека макросов повреждена. Исходный файл сохранён; запись в библиотеку отключена.")
            color: Theme.warning; font.pixelSize: 14
        }
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: root.windowRef.tr("Библиотека макросов"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 20; Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("Закрыть"); onClicked: root.close() }
        }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Кнопка назначения")+": "+(root.controller.buttons.find(b=>b.index===root.controller.selectedButton) || {label:"—"}).label
            color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14
        }
        RowLayout {
            Layout.fillWidth: true
            CutCombo {
                objectName: "macro-library-selector"
                Layout.fillWidth: true; model: root.controller.macroLibrary; textRole: "name"
                currentIndex: root.controller.macroLibrary.findIndex(e=>e.id===root.controller.selectedLibraryMacro)
                enabled: !root.controller.recording
                onActivated: i=>root.controller.selectLibraryMacro(root.controller.macroLibrary[i].id)
            }
            CutButton { text: root.windowRef.tr("Новый макрос"); enabled: !root.controller.recording; onClicked: root.controller.createLibraryMacro(root.windowRef.tr("Макрос")+" "+(root.controller.macroLibrary.length+1)) }
            CutButton { text: root.windowRef.tr("Удалить"); enabled: !root.controller.recording && root.controller.selectedLibraryMacro.length>0; onClicked: root.controller.deleteLibraryMacro(root.controller.selectedLibraryMacro) }
        }
        RowLayout {
            Layout.fillWidth: true
            CutInput {
                id: name
                objectName: "macro-name"
                Layout.fillWidth: true; maximumLength: 64; enabled: !root.controller.recording
                placeholderText: root.windowRef.tr("Название макроса")
                Component.onCompleted: text=root.controller.libraryMacroName
                onEditingFinished: { if (text.trim().length>0) root.controller.saveLibraryMacro(text) }
            }
            CutButton { text: root.windowRef.tr("Сохранить в библиотеку"); enabled: !root.controller.recording && name.text.trim().length>0; onClicked: root.controller.saveLibraryMacro(name.text) }
        }
        Flow {
            visible: root.controller.eweadnEditor
            Layout.fillWidth: true; Layout.preferredHeight: visible ? implicitHeight : 0
            spacing: 5
            Repeater {
                model: [{id:"once",label:root.windowRef.tr("Один раз")},{id:"toggle",label:root.windowRef.tr("До повторного нажатия")},{id:"held",label:root.windowRef.tr("Пока кнопка удерживается")}]
                delegate: CutButton {
                    required property var modelData
                    text: modelData.label; selected: root.controller.libraryRepeatMode===modelData.id
                    enabled: !root.controller.recording && root.controller.libraryMacroName.length>0
                    onClicked: root.controller.setLibraryRepeatMode(modelData.id)
                }
            }
        }
        StyledText {
            visible: root.controller.eweadnEditor
            text: root.windowRef.tr("Режим сохранён в локальной библиотеке; аппаратная передача макросов S9 пока недоступна.")
            font.family: Theme.displayFont; font.pixelSize: 12; color: Theme.warning; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
        RowLayout {
            Layout.fillWidth: true
            CutButton {
                objectName: "macro-record-toggle"
                text: root.controller.recording ? root.windowRef.tr("Остановить запись") : root.windowRef.tr("Начать запись")
                selected: root.controller.recording; enabled: root.controller.macroCaptureAvailable && !root.controller.busy
                onClicked: {
                    if (root.controller.recording) root.controller.stopRecording()
                    else { root.controller.beginMacroCapture(root,capture); capture.forceActiveFocus() }
                }
            }
            CutButton { text: root.windowRef.tr("Записывать паузы"); quietSelected: true; selected: root.controller.capturePauses; enabled: !root.controller.recording; onClicked: root.controller.setCapturePauses(!root.controller.capturePauses) }
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("Очистить"); enabled: !root.controller.recording; onClicked: root.controller.clearMacro() }
        }
        Rectangle {
            id: capture
            objectName: "macro-capture-area"
            Layout.fillWidth: true; Layout.preferredHeight: 96
            color: Theme.surface2; border.width: 1; border.color: root.controller.recording ? Theme.accent : Theme.borderStrong
            StyledText {
                anchors.fill: parent; anchors.margins: 12
                text: root.controller.recording ? root.windowRef.tr("Запись: нажимай клавиши и щёлкай в этой области. Остановка — кнопкой выше.") : root.windowRef.tr("Здесь записываются щелчки. Клавиши записываются только пока это окно активно.")
                color: root.controller.recording ? Theme.accent : Theme.text; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap; verticalAlignment: Text.AlignVCenter
            }
            MouseArea { anchors.fill: parent; acceptedButtons: Qt.AllButtons; onPressed: capture.forceActiveFocus() }
        }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Библиотека хранится локально. Сохранение не меняет мышь. Системные сочетания Wayland могут перехватываться рабочим столом.")
            color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
        }
        ListView {
            objectName: "macro-events"
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
            model: root.controller.macroEvents
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                required property var modelData
                width: ListView.view.width; height: 36
                StyledText { text: modelData.label; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13; Layout.fillWidth: true }
                CutButton { text: "×"; enabled: !root.controller.recording; Accessible.name: root.windowRef.tr("Удалить событие"); onClicked: root.controller.removeEvent(modelData.index) }
            }
        }
        RowLayout {
            enabled: !root.controller.recording; Layout.fillWidth: true
            NumberInput { numberValue: root.delay; Layout.preferredWidth: 90; onNumberCommitted: value=>root.delay=Math.round(value) }
            CutButton { text: root.windowRef.tr("Добавить паузу"); onClicked: root.controller.addPause(root.delay) }
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("Применить макрос"); primary: true; enabled: root.controller.macroSupported && !root.controller.busy && root.controller.available && !root.controller.macroConflict; onClicked: root.controller.applyMacro() }
        }
        StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.controller.message; color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13 }
    }
}
