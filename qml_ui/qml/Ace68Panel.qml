pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    property string metric: "actuation"
    readonly property string section: controller.section
    readonly property var fields: controller.aceFields
    readonly property var selected: controller.aceSelectedKeys
    readonly property var keyFields: ["actuation","rapid_trigger","rt_press","rt_release","press_dead_zone","release_dead_zone"]
    function field(name) { return fields["mchose-ace68:"+name] || null }
    function keyField(name) { return fields["key:"+controller.selectedKey+":"+name] || null }
    function effectLabel(value) {
        const mode=field("lighting_mode"), index=mode ? mode.choices.indexOf(value) : -1
        return index>=0 ? mode.choiceLabels[index] : value
    }
    function tint() {
        const color=field("lighting")
        const rgb=color ? color.value : null
        return rgb && field("lighting_mode") && field("lighting_mode").value!=="Off" ? Qt.rgba(rgb[0]/255,rgb[1]/255,rgb[2]/255,.55) : "transparent"
    }
    spacing: 12
    Ace68Keyboard {
        controller: root.controller; windowRef: root.windowRef
        showValues: root.section==="keys"; metric: root.metric
        previewColor: root.section==="lighting" ? root.tint() : "transparent"
    }
    Flow {
        visible: ["keys","lighting"].includes(root.section)
        Layout.fillWidth: true; spacing: 6
        Repeater {
            model: [{id:"wasd",label:root.windowRef.tr("Выбрать WASD")},{id:"all",label:root.windowRef.tr("Выбрать все")},{id:"inverse",label:root.windowRef.tr("Инвертировать выбор")},{id:"none",label:root.windowRef.tr("Снять выделение")}]
            delegate: CutButton {
                required property var modelData
                objectName: "ace-select-"+modelData.id
                text: modelData.label; enabled: !root.controller.busy
                onClicked: root.controller.selectAceKeys(modelData.id)
            }
        }
        CutCombo {
            visible: root.section==="keys"
            model: [root.windowRef.tr("Точка срабатывания, мм"),"Rapid Trigger",root.windowRef.tr("Верхняя мёртвая зона, мм")]
            onActivated: index => root.metric=["actuation","rapid_trigger","press_dead_zone"][index]
            Accessible.name: root.windowRef.tr("Значения на схеме")
        }
    }
    Ace68Assignments { visible: root.section==="key_assignments"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
    Ace68Advanced { visible: root.section==="advanced_keys"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
    ColumnLayout {
        visible: root.section==="lighting" && root.field("lighting_mode") && root.field("lighting_mode").value==="Custom"
        Layout.fillWidth: true
        CutButton { text: root.windowRef.tr("Прочитать поклавишные цвета"); enabled: !root.controller.busy; onClicked: root.controller.readAceColors() }
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr("Сначала примени режим поклавишных цветов, затем прочитай банк и выбери клавиши. Цвета сохраняются в клавиатуре; приложение не запускает анимацию.")
            color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
        }
        Loader {
            Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
            active: !!root.fields["ace:color:"+root.controller.selectedKey]
            sourceComponent: ControlEditor {
                field: Object.assign({},root.fields["ace:color:"+root.controller.selectedKey],{value:root.controller.aceColorSelection.value,writable:root.controller.aceColorSelection.writable,mixed:root.controller.aceColorSelection.mixed})
                controller: root.controller; windowRef: root.windowRef
                editValue: value => root.controller.editAceColor(value)
            }
        }
    }
    StyledText {
        visible: root.section==="keys"
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Изменения относятся к выбранным клавишам. «Применить» сохраняет все черновики срабатывания текущего профиля.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
    }
    EmptyState {
        visible: root.section==="keys" && root.selected.length===0
        Layout.fillWidth: true; Layout.preferredHeight: 100
        title: root.windowRef.tr("Выбери клавиши на схеме")
        detail: root.windowRef.tr("Можно выбрать несколько клавиш или воспользоваться кнопкой WASD.")
    }
    GridLayout {
        visible: root.section==="keys" && root.selected.length>0
        Layout.fillWidth: true; columns: width>=1050 ? 3 : width>=730 ? 2 : 1
        columnSpacing: 12; rowSpacing: 12
        Repeater {
            model: root.keyFields
            delegate: Loader {
                id: trigger
                required property string modelData
                Layout.fillWidth: true; Layout.preferredWidth: 320; Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: item ? item.implicitHeight : 0
                active: !!root.keyField(modelData)
                sourceComponent: ControlEditor {
                    field: root.keyField(trigger.modelData)
                    controller: root.controller; windowRef: root.windowRef
                    editValue: value => root.controller.editAceKeys(trigger.modelData,value)
                }
            }
        }
    }
    GridLayout {
        visible: root.section==="lighting"
        Layout.fillWidth: true; columns: width>=1050 ? 3 : width>=730 ? 2 : 1
        columnSpacing: 12; rowSpacing: 12
        CutCard {
            Layout.fillWidth: true; Layout.preferredWidth: 320; Layout.alignment: Qt.AlignTop
            Layout.preferredHeight: effects.implicitHeight+32
            ColumnLayout {
                id: effects
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                spacing: 10
                StyledText { text: root.windowRef.tr("Эффекты подсветки"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16 }
                ScrollView {
                    id: effectScroll
                    Layout.fillWidth: true; Layout.preferredHeight: 240
                    contentWidth: availableWidth; clip: true
                    GridLayout {
                    width: effectScroll.availableWidth; columns: 2; columnSpacing: 6; rowSpacing: 6
                    Repeater {
                        model: root.field("lighting_mode") ? root.field("lighting_mode").choices : []
                        delegate: CutButton {
                            required property string modelData
                            objectName: "ace-mode-"+modelData
                            text: root.effectLabel(modelData)
                            Layout.fillWidth: true; Layout.preferredWidth: 140; Layout.minimumWidth: 0
                            implicitHeight: 44
                            contentItem: StyledText { text: parent.text; color: parent.selected ? Theme.accent : Theme.text; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                            selected: !!root.field("lighting_mode") && root.field("lighting_mode").value===modelData; quietSelected: true
                            enabled: !!root.field("lighting_mode") && root.field("lighting_mode").writable && !root.controller.busy
                            onClicked: root.controller.edit("mchose-ace68:lighting_mode",modelData)
                        }
                    }
                    }
                }
                StyledText { text: root.windowRef.tr("На схеме показан предпросмотр, а не измеренное свечение клавиш."); color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.preferredWidth: 320; Layout.alignment: Qt.AlignTop
            Repeater {
                model: ["lighting_speed","brightness","lighting_direction"]
                delegate: Loader {
                    id: lightingParameter
                    required property string modelData
                    Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
                    active: !!root.field(modelData)
                    sourceComponent: ControlEditor { field: root.field(lightingParameter.modelData); controller: root.controller; windowRef: root.windowRef }
                }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.preferredWidth: 320; Layout.alignment: Qt.AlignTop
            Repeater {
                model: ["lighting_palette","lighting"]
                delegate: Loader {
                    id: palette
                    required property string modelData
                    Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
                    active: !!root.field(modelData)
                    sourceComponent: ControlEditor { field: root.field(palette.modelData); controller: root.controller; windowRef: root.windowRef }
                }
            }
        }
    }
    GridLayout {
        visible: ["performance","profiles"].includes(root.section)
        Layout.fillWidth: true; columns: width>=730 ? 2 : 1
        Repeater {
            model: root.section==="performance" ? ["polling_rate","win_lock","key_debounce","keyboard_mode","stability_mode","adaptive_calibration"] : ["profiles"]
            delegate: Loader {
                id: other
                required property string modelData
                Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
                active: !!root.field(modelData)
                sourceComponent: ControlEditor { field: root.field(other.modelData); controller: root.controller; windowRef: root.windowRef }
            }
        }
    }
    CutCard {
        visible: root.section==="profiles"
        Layout.fillWidth: true; Layout.preferredHeight: unavailable.implicitHeight+32
        ColumnLayout {
            id: unavailable
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 10
            StyledText {
                text: root.windowRef.tr("Возможности, требующие проверки протокола")
                color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16
            }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Калибровка, смена типа переключателя, точности и прошивки не выполняются из этого редактора.")
                color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14
            }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Пункты из M HUB не становятся доступными для записи только по наличию на скриншоте. Существующая конфигурация сохраняется.")
                color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
            }
        }
    }
}
