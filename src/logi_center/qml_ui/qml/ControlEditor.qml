pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

CutCard {
    id: root
    required property var field
    required property var controller
    required property var windowRef
    readonly property var currentField: field || ({id:"",label:"",kind:"readonly",choices:[],choiceLabels:[],value:null,observed:"",source:"",minimum:0,maximum:100,step:1,writable:false,dirty:false,conflict:false,state:""})
    property var editValue: null
    function stage(value) {
        if (!field || !field.writable || controller.busy || !controller.available) return
        if (editValue) editValue(value)
        else controller.edit(field.id,value)
    }
    implicitHeight: content.implicitHeight+24
    inset: 12
    ColorDialog {
        id: picker
        title: root.windowRef.tr("Выбери цвет подсветки")
        selectedColor: root.currentField.kind === "color" && root.currentField.value ? Qt.rgba(root.currentField.value[0]/255,root.currentField.value[1]/255,root.currentField.value[2]/255,1) : "white"
        onAccepted: root.stage([Math.round(selectedColor.r*255),Math.round(selectedColor.g*255),Math.round(selectedColor.b*255)])
    }
    ColumnLayout {
        id: content
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
        spacing: 7
        RowLayout {
            Layout.fillWidth: true
            StyledText { text: root.currentField.label; font.family: Theme.displayFont; font.pixelSize: 15; color: Theme.text; wrapMode: Text.Wrap; Layout.fillWidth: true }
            StyledText { text: root.currentField.conflict ? root.windowRef.tr("Конфликт черновика") : root.currentField.dirty ? root.windowRef.tr(root.currentField.state === "sent_unverified" ? "Отправлено, не подтверждено" : "Не сохранено") : ""; color: root.currentField.conflict ? Theme.error : Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.maximumWidth: 160 }
        }
        StyledText { visible: root.currentField.mixed===true; text: root.windowRef.tr("Разные значения"); color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            CutCombo {
                visible: root.currentField.kind === "choice"
                Layout.fillWidth: true
                Layout.maximumWidth: root.currentField.indicatorColor ? 280 : 360
                model: root.currentField.choiceLabels
                currentIndex: root.currentField.choices.indexOf(root.currentField.value)
                enabled: root.currentField.writable && !root.controller.busy
                onActivated: index => root.stage(root.currentField.choices[index])
            }
            Rectangle {
                objectName: "dpi-stage-swatch"
                visible: !!root.currentField.indicatorColor
                Layout.preferredWidth: 18; Layout.preferredHeight: 18
                radius: 9
                color: root.currentField.indicatorColor || "transparent"
                border.color: Theme.borderStrong
                border.width: 1
            }
            CutSlider {
                visible: root.currentField.kind === "number"
                Layout.fillWidth: true
                from: root.currentField.minimum; to: root.currentField.maximum; stepSize: root.currentField.step
                value: typeof root.currentField.value === "number" ? root.currentField.value : from
                enabled: root.currentField.writable && !root.controller.busy
                onMoved: root.stage(Math.round(value*1000)/1000)
            }
            NumberInput {
                objectName: "control-value-"+root.currentField.id
                visible: root.currentField.kind === "number"
                Layout.preferredWidth: 86
                numberValue: root.currentField.value
                enabled: root.currentField.writable && !root.controller.busy
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                onNumberCommitted: value => root.stage(value)
            }
            CutButton {
                visible: root.currentField.kind === "bool"
                text: root.currentField.value ? root.windowRef.tr("Включено") : root.windowRef.tr("Выключено")
                selected: root.currentField.value === true
                enabled: root.currentField.writable && !root.controller.busy
                onClicked: root.stage(!root.currentField.value)
            }
            CutButton {
                visible: root.currentField.kind === "color"
                text: root.windowRef.tr("Выбрать цвет")
                enabled: root.currentField.writable && !root.controller.busy
                onClicked: picker.open()
            }
            Rectangle {
                visible: root.currentField.kind === "color"
                Layout.preferredWidth: 62; Layout.preferredHeight: 29
                border.color: Theme.borderStrong
                color: root.currentField.kind === "color" && root.currentField.value ? Qt.rgba(root.currentField.value[0]/255,root.currentField.value[1]/255,root.currentField.value[2]/255,1) : "transparent"
            }
            StyledText { visible: root.currentField.kind === "readonly"; text: root.currentField.observed; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
        }
        RowLayout {
            visible: root.currentField.id.indexOf(":duration:") >= 0
            spacing: 6
            CutButton { text: root.windowRef.tr("Медленно"); enabled: root.currentField.writable && !root.controller.busy; onClicked: root.controller.edit(root.currentField.id,8000) }
            CutButton { text: root.windowRef.tr("Обычно"); enabled: root.currentField.writable && !root.controller.busy; onClicked: root.controller.edit(root.currentField.id,5000) }
            CutButton { text: root.windowRef.tr("Быстро"); enabled: root.currentField.writable && !root.controller.busy; onClicked: root.controller.edit(root.currentField.id,2600) }
        }
        StyledText {
            Layout.fillWidth: true
            text: root.currentField.proposed ? root.windowRef.tr("Для нового режима предложено значение; оно ещё не применено.") : (root.currentField.cached || root.currentField.stale ? root.windowRef.tr("Последнее значение: ") : root.windowRef.tr("Сейчас: "))+root.currentField.observed+" · "+root.currentField.source+(root.currentField.stale ? " · "+root.windowRef.tr("Актуальность не подтверждена") : "")+(root.currentField.writable ? "" : " · "+root.windowRef.tr("Только чтение"))
            color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap
        }
        StyledText { visible: !!root.currentField.note; text: root.currentField.note || ""; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true }
        StyledText {
            visible: !!root.currentField.legacyDraft
            text: root.windowRef.tr("Старый черновик без профиля или ступени: %1. Проверь значение и выбери его заново.").replace("%1", root.currentField.legacyDraft || "")
            color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12
            wrapMode: Text.Wrap; Layout.fillWidth: true
        }
        StyledText {
            visible: root.currentField.state.length>0 && root.currentField.state !== "draft"
            text: root.currentField.state === "sent_unverified" ? root.windowRef.tr("Отправлено · без аппаратного подтверждения") : root.currentField.state === "confirmed" ? root.windowRef.tr("Проверено") : root.currentField.state === "local_saved_only" ? root.windowRef.tr("Сохранено локально") : root.currentField.state === "mismatch" ? root.windowRef.tr("Результат отличается") : root.windowRef.tr("Проверь результат операции")
            color: root.currentField.state === "mismatch" || root.currentField.state === "error" ? Theme.error : Theme.muted
            font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
    }
}
