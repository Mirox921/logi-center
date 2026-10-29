pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    property string category: "basic"
    property int modifiers: 1
    readonly property var selection: controller.aceBindingSelection
    spacing: 10
    Flow {
        Layout.fillWidth: true; spacing: 6
        Repeater {
            model: ["Windows","Windows Fn","Mac","Mac Fn"]
            delegate: CutButton {
                required property int index
                required property string modelData
                text: modelData; selected: root.controller.aceLayer===index; quietSelected: true
                enabled: !root.controller.busy
                onClicked: root.controller.setAceLayer(index)
            }
        }
        CutButton { text: root.windowRef.tr("Прочитать назначения"); enabled: !root.controller.busy && root.controller.available; onClicked: root.controller.readAceBindings() }
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Выбранный слой редактируется отдельно; просмотр слоя не переключает режим клавиатуры.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.controller.busy ? root.windowRef.tr("Выполняется…") : root.selection.available ?
              root.windowRef.tr("Текущее назначение")+": "+root.selection.label : root.windowRef.tr("Назначения ещё не прочитаны.")
        color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 15
    }
    Flow {
        Layout.fillWidth: true; spacing: 6
        Repeater {
            model: [{id:"basic",label:root.windowRef.tr("Клавиатура")},{id:"mouse",label:root.windowRef.tr("Мышь")},{id:"media",label:root.windowRef.tr("Мультимедиа")},
                    {id:"lighting",label:root.windowRef.tr("Подсветка")},{id:"shortcuts",label:root.windowRef.tr("Сочетания")}]
            delegate: CutButton {
                required property var modelData
                text: modelData.label; selected: root.category===modelData.id; quietSelected: true
                onClicked: root.category=modelData.id
            }
        }
        CutInput { id: search; placeholderText: root.windowRef.tr("Поиск действия"); Accessible.name: placeholderText }
    }
    Flow {
        visible: root.category==="shortcuts"
        Layout.fillWidth: true; spacing: 5
        Repeater {
            model: ["Ctrl","Shift","Alt","Super"]
            delegate: CutButton {
                required property int index
                required property string modelData
                text: modelData; selected: !!(root.modifiers&(1<<index)); quietSelected: true
                onClicked: root.modifiers=root.modifiers^(1<<index)
            }
        }
        CutCombo {
            id: key
            model: root.controller.aceActions.filter(action => action.group==="basic" && action.value[0]===16 && action.value[1]===0)
            textRole: "label"
        }
        CutButton {
            text: root.windowRef.tr("Назначить сочетание"); enabled: root.selection.writable && !root.controller.busy && key.currentIndex>=0
            onClicked: root.controller.editAceBinding([16,root.modifiers,key.model[key.currentIndex].value[2]])
        }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: width>=1000 ? 8 : width>=720 ? 6 : 4
        columnSpacing: 5; rowSpacing: 5
        Repeater {
            model: root.controller.aceActions
            delegate: CutButton {
                required property var modelData
                visible: modelData.group===root.category && (search.text.length===0 || modelData.label.toLowerCase().includes(search.text.toLowerCase()))
                Layout.fillWidth: true; Layout.preferredWidth: 100; Layout.minimumWidth: 0
                text: modelData.label
                enabled: root.selection.writable && !root.controller.busy
                ToolTip.visible: hovered; ToolTip.text: modelData.label
                onClicked: root.controller.editAceBinding(modelData.value)
            }
        }
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Действие добавляется в черновик выбранных клавиш. Запись — после «Применить». Последняя Fn-клавиша защищена.")
        color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
    }
}
