pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    objectName: "k7-button-panel"
    required property var controller
    required property var windowRef
    property string category: "system"
    property int modifiers: 1
    readonly property var selected: controller.k7Fields["mchose:button_bindings:"+controller.k7SelectedButton] || ({writable:false,dirty:false,value:[]})
    readonly property var buttons: controller.k7Buttons
    readonly property bool wide: width>=900
    function matches(action) { return action.group===category && (search.text.length===0 || action.label.toLowerCase().includes(search.text.toLowerCase())) }
    function assigned(value) { return JSON.stringify(root.selected.value)===JSON.stringify(value) }
    spacing: 12
    GridLayout {
        Layout.fillWidth: true
        columns: root.wide ? 2 : 1
        columnSpacing: 14; rowSpacing: 14
        CutCard {
            Layout.row: root.wide ? 0 : 1; Layout.column: 0
            Layout.preferredWidth: root.wide ? 290 : -1; Layout.fillWidth: !root.wide
            Layout.preferredHeight: library.implicitHeight+32
            ColumnLayout {
                id: library
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                spacing: 10
                StyledText { text: root.windowRef.tr("Назначение кнопки"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16 }
                CutInput { id: search; Layout.fillWidth: true; placeholderText: root.windowRef.tr("Поиск действия"); Accessible.name: placeholderText }
                Flow {
                    Layout.fillWidth: true; spacing: 5
                    Repeater {
                        model: [{id:"system",label:root.windowRef.tr("Мышь / DPI")},{id:"keyboard",label:root.windowRef.tr("Клавиатура")},{id:"hotkey",label:root.windowRef.tr("Сочетания")},{id:"media",label:root.windowRef.tr("Мультимедиа")}]
                        delegate: CutButton {
                            required property var modelData
                            objectName: "k7-action-category-"+modelData.id
                            text: modelData.label; selected: root.category===modelData.id; quietSelected: true
                            onClicked: root.category=modelData.id
                        }
                    }
                }
                ColumnLayout {
                    visible: root.category==="hotkey"
                    Layout.fillWidth: true; spacing: 6
                    Flow {
                        Layout.fillWidth: true; spacing: 4
                        Repeater {
                            model: ["Ctrl","Shift","Alt","Super"]
                            delegate: CutButton {
                                required property int index
                                required property string modelData
                                text: modelData; selected: !!(root.modifiers & (1<<index)); quietSelected: true
                                onClicked: root.modifiers=root.modifiers ^ (1<<index)
                            }
                        }
                    }
                    CutCombo {
                        id: hotkey
                        objectName: "k7-hotkey-key"
                        Layout.fillWidth: true
                        model: root.controller.k7Actions.filter(action => action.group==="keyboard")
                        textRole: "label"
                    }
                    CutButton {
                        objectName: "k7-hotkey-assign"
                        Layout.fillWidth: true
                        text: root.windowRef.tr("Назначить сочетание")
                        enabled: root.selected.writable && !root.controller.busy && hotkey.currentIndex>=0
                        onClicked: root.controller.edit("mchose:button_bindings:"+root.controller.k7SelectedButton,
                            [2,root.modifiers*65536+hotkey.model[hotkey.currentIndex].value[1]])
                    }
                }
                ScrollView {
                    Layout.fillWidth: true; Layout.preferredHeight: 290
                    contentWidth: availableWidth; clip: true
                    ColumnLayout {
                        width: library.width; spacing: 4
                        Repeater {
                            model: root.controller.k7Actions
                            delegate: CutButton {
                                required property var modelData
                                visible: root.matches(modelData)
                                Layout.fillWidth: true
                                text: modelData.label; selected: root.assigned(modelData.value); quietSelected: true
                                enabled: root.selected.writable && !root.controller.busy
                                onClicked: root.controller.edit("mchose:button_bindings:"+root.controller.k7SelectedButton,modelData.value)
                            }
                        }
                    }
                }
            }
        }
        CutCard {
            Layout.row: 0; Layout.column: root.wide ? 1 : 0
            Layout.fillWidth: true; Layout.preferredHeight: diagramContent.implicitHeight+32
            ColumnLayout {
                id: diagramContent
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                spacing: 10
                StyledText { text: "MCHOSE K7 Ultra"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 17 }
                Item {
                    id: diagram
                    Layout.fillWidth: true; Layout.preferredHeight: 400
                    Image {
                        id: mouse
                        anchors.centerIn: parent; height: parent.height; width: height*400/600
                        source: "../assets/diagrams/k7-buttons.svg"; sourceSize: Qt.size(800,1200); fillMode: Image.PreserveAspectFit
                    }
                    Canvas {
                        id: connectors
                        anchors.fill: parent
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        Connections { target: root.controller; function onChanged() { connectors.requestPaint() } }
                        onPaint: {
                            const ctx=getContext("2d"); ctx.reset(); ctx.lineWidth=1
                            for (let b of root.buttons) {
                                const right=b.index===2 || b.index===1
                                const ax=mouse.x+b.x*mouse.width, ay=mouse.y+b.y*mouse.height
                                const labelY=(b.index===0 || b.index===2 ? .17 : b.index===1 ? .33 : b.index===3 ? .49 : .65)*height
                                const endX=right ? width-156 : 156
                                ctx.strokeStyle=root.controller.k7SelectedButton===b.index ? Theme.accent : Theme.borderStrong
                                ctx.beginPath(); ctx.moveTo(ax,ay); ctx.lineTo(right ? ax+15 : ax-15,labelY+18); ctx.lineTo(endX,labelY+18); ctx.stroke()
                            }
                        }
                    }
                    Repeater {
                        model: root.buttons
                        delegate: Item {
                            id: target
                            required property var modelData
                            readonly property bool rightSide: modelData.index===2 || modelData.index===1
                            anchors.fill: parent
                            CutButton {
                                objectName: "k7-button-label-"+target.modelData.index
                                x: target.rightSide ? diagram.width-width : 0
                                y: (target.modelData.index===0 || target.modelData.index===2 ? .17 : target.modelData.index===1 ? .33 : target.modelData.index===3 ? .49 : .65)*diagram.height
                                width: 156; text: target.modelData.label
                                selected: root.controller.k7SelectedButton===target.modelData.index; quietSelected: true
                                onClicked: root.controller.selectK7Button(target.modelData.index)
                            }
                            Rectangle {
                                objectName: "k7-button-anchor-"+target.modelData.index
                                x: mouse.x+target.modelData.x*mouse.width-width/2
                                y: mouse.y+target.modelData.y*mouse.height-height/2
                                width: 20; height: 20; radius: 10
                                color: root.controller.k7SelectedButton===target.modelData.index ? Theme.accent : Theme.surface2
                                border.color: root.controller.k7SelectedButton===target.modelData.index ? Theme.accent : Theme.text
                                MouseArea { anchors.fill: parent; onClicked: root.controller.selectK7Button(target.modelData.index) }
                            }
                        }
                    }
                }
                CutCombo {
                    Layout.fillWidth: true
                    model: root.buttons; textRole: "label"
                    currentIndex: root.buttons.findIndex(b => b.index===root.controller.k7SelectedButton)
                    onActivated: index => root.controller.selectK7Button(root.buttons[index].index)
                }
                StyledText {
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                    text: (root.buttons.find(b => b.index===root.controller.k7SelectedButton) || {}).assignment || ""
                    color: root.selected.dirty ? Theme.warning : Theme.muted
                    font.family: Theme.dataFont; font.pixelSize: 13
                }
            }
        }
    }
    StyledText {
        visible: !root.selected.writable
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.selected.note || root.windowRef.tr("Только чтение")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Сначала выбери кнопку на схеме, затем действие. Запись — только после «Применить». Хотя бы одна кнопка должна сохранять левый щелчок.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Редактор сложных макросов K7 пока недоступен: формат записи не проверен. Существующие макросы не изменяются.")
        color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
    }
}
