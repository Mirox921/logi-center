pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Theme 1.0

ColumnLayout {
    id: root
    objectName: "eweadn-panel"
    required property var controller
    required property var windowRef
    signal chooseArtwork()
    readonly property bool ready: !!controller.eweadnState.model_id
    readonly property var selected: controller.eweadnFields["eweadn:button_bindings:"+controller.selectedButton] || ({value:[],writable:false})
    property string actionGroup: "mouse"
    property int colorStage: 0
    property string colorContext: ""
    property int hoveredButton: -1
    function assignmentLabel(value) {
        const action=root.controller.eweadnActions.find(entry=>JSON.stringify(entry.value)===JSON.stringify(value))
        if (action) return action.label
        if (value[0]===0) return root.windowRef.tr("Исходное назначение")
        if (value[0]===6) return root.windowRef.tr("Макрос")+" M"+value[3]
        return root.windowRef.tr("Действие устройства")
    }
    function openStageColor(index) {
        root.colorStage=index
        root.colorContext=root.controller.eweadnContext
        const field=root.controller.eweadnFields["eweadn:dpi_config:color"+index]
        if (field) colorPicker.selectedColor=Qt.rgba(field.value[0]/255,field.value[1]/255,field.value[2]/255,1)
        colorPicker.open()
    }
    spacing: 12
    MacroWindow { id: macros; controller: root.controller; windowRef: root.windowRef }
    ColorDialog {
        id: colorPicker
        title: root.windowRef.tr("Выбери цвет подсветки")
        onAccepted: if (root.colorContext===root.controller.eweadnContext) root.controller.edit("eweadn:dpi_config:color"+root.colorStage,[Math.round(selectedColor.r*255),Math.round(selectedColor.g*255),Math.round(selectedColor.b*255)])
    }
    Dialog {
        id: resetDialog
        property string context: ""
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        title: root.windowRef.tr("Сброс всех настроек")
        width: Math.min(root.windowRef.width-32,540)
        height: Math.min(root.windowRef.height-48,310)
        background: CutFrame { fillColor: Theme.surface1; lineColor: Theme.warning; cut: Theme.cut }
        contentItem: StyledText {
            text: root.windowRef.tr("Мышь вернётся к заводским настройкам: DPI, кнопки и другие сохранённые параметры могут быть потеряны. Создаётся частный снимок читаемых параметров; аппаратная библиотека макросов в него не входит. Полный откат не гарантируется. Продолжить?")
            color: Theme.warning; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap
        }
        footer: RowLayout {
            implicitHeight: 44
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("Отменить"); onClicked: resetDialog.reject() }
            CutButton { text: root.windowRef.tr("Сбросить"); enabled: root.controller.available && !root.controller.busy; onClicked: resetDialog.accept() }
        }
        onAccepted: root.controller.resetEweadn(true,context)
    }
    EmptyState {
        visible: !root.ready; Layout.fillWidth: true; Layout.preferredHeight: 160
        title: root.controller.busy ? root.windowRef.tr("Выполняется…") : root.windowRef.tr("Настройки устройства недоступны")
        detail: root.windowRef.tr("Проверь подключение по USB или приёмнику, закрой веб-конфигуратор и пошевели мышью для пробуждения.")
    }
    GridLayout {
        visible: root.ready && root.controller.section==="buttons"
        Layout.fillWidth: true
        columns: width>=900 ? 2 : 1
        columnSpacing: 12; rowSpacing: 12
        CutCard {
            Layout.fillWidth: true; Layout.preferredWidth: 650; Layout.preferredHeight: Math.max(300,Math.min(480,root.windowRef.height-400))
            Item {
                id: diagram
                anchors.fill: parent; clip: true
                Image {
                    id: mouse
                    y: 68; height: diagram.height-76; width: height*250/485
                    anchors.horizontalCenter: parent.horizontalCenter
                    source: root.ready ? Theme.assetRoot + "mice/eweadn-s9.svg" : ""
                    sourceSize.width: Math.min(1024,Math.ceil(width*2))
                    fillMode: Image.PreserveAspectFit; asynchronous: true
                    objectName: "eweadn-button-artwork"
                }
                Canvas {
                    id: lines
                    anchors.fill: parent
                    onPaint: {
                        const ctx=getContext("2d"); ctx.reset();ctx.lineWidth=1.4
                        for (const button of root.controller.eweadnButtons) {
                            if (!button.selected && root.hoveredButton!==button.index) continue
                            const px=mouse.x+button.x*mouse.width, py=mouse.y+button.y*mouse.height
                            const side=button.index>=3
                            const ex=side ? Math.min(125,diagram.width*0.25) : diagram.width*({0:.18,2:.50,1:.82})[button.index]
                            const ey=side ? mouse.y+(button.index===4 ? .40 : .60)*mouse.height : 38
                            ctx.strokeStyle=button.selected ? Theme.accent : Theme.muted
                            ctx.beginPath();ctx.moveTo(px,py)
                            if (side) {ctx.lineTo(Math.max(ex+8,mouse.x-10),py);ctx.lineTo(Math.max(ex+8,mouse.x-10),ey);ctx.lineTo(ex,ey)}
                            else {ctx.lineTo(ex,ey+14);ctx.lineTo(ex,ey)}
                            ctx.stroke()
                        }
                    }
                }
                Connections { target: root.controller; function onChanged() { lines.requestPaint() } }
                Connections { target: root; function onHoveredButtonChanged() { lines.requestPaint() } }
                onWidthChanged: lines.requestPaint()
                Repeater {
                    model: root.controller.eweadnButtonModel
                    delegate: CutButton {
                        required property var capability
                        readonly property var modelData: capability
                        objectName: "eweadn-button-label-"+modelData.index
                        width: modelData.index>=3 ? Math.min(125,diagram.width*.25) : Math.min(150,diagram.width*.29)
                        x: modelData.index>=3 ? 0 : diagram.width*({0:.18,2:.50,1:.82})[modelData.index]-width/2
                        y: modelData.index>=3 ? mouse.y+(modelData.index===4 ? .40 : .60)*mouse.height-height/2 : 0
                        text: modelData.label; selected: modelData.selected; quietSelected: true
                        onClicked: root.controller.selectButton(modelData.index)
                        onHoveredChanged: root.hoveredButton=hovered ? modelData.index : -1
                    }
                }
                Repeater {
                    model: root.controller.eweadnButtonModel
                    delegate: Item {
                        id: marker
                        required property var capability
                        readonly property var modelData: capability
                        x: mouse.x+modelData.x*mouse.width-12; y: mouse.y+modelData.y*mouse.height-12
                        width: 24; height: 24
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.modelData.selected ? 9 : 5; height: width; radius: width/2
                            color: parent.modelData.selected ? Theme.accent : Theme.muted
                        }
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true
                            objectName: "eweadn-button-hit-"+parent.modelData.index
                            onClicked: root.controller.selectButton(parent.modelData.index)
                            onEntered: root.hoveredButton=parent.modelData.index
                            onExited: root.hoveredButton=-1
                            ToolTip.visible: containsMouse; ToolTip.text: marker.modelData.label
                        }
                    }
                }
            }
        }
        CutCard {
            Layout.fillWidth: true; Layout.preferredWidth: 340; Layout.alignment: Qt.AlignTop
            implicitHeight: assignment.implicitHeight+32
            ColumnLayout {
                id: assignment
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                spacing: 10
                StyledText { text: root.windowRef.tr("Назначение кнопки"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18 }
                StyledText { text: root.windowRef.tr(root.selected.dirty ? "Черновик: " : "Сейчас: ")+root.assignmentLabel(root.selected.value); color: root.selected.dirty ? Theme.warning : Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Flow {
                    Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 5
                    Repeater {
                        model: [{id:"mouse",label:root.windowRef.tr("Мышь")},{id:"keyboard",label:root.windowRef.tr("Клавиатура")},{id:"media",label:root.windowRef.tr("Мультимедиа")}]
                        delegate: CutButton {
                            required property var modelData
                            text: modelData.label; selected: root.actionGroup===modelData.id
                            onClicked: root.actionGroup=modelData.id
                        }
                    }
                }
                CutCombo {
                    id: action
                    Layout.fillWidth: true
                    model: root.controller.eweadnActions.filter(entry=>entry.group===root.actionGroup)
                    textRole: "label"; enabled: root.selected.writable && !root.controller.busy
                }
                CutButton {
                    text: root.windowRef.tr("Назначить")
                    enabled: root.selected.writable && action.currentIndex>=0 && !root.controller.busy
                    onClicked: root.controller.edit("eweadn:button_bindings:"+root.controller.selectedButton,action.model[action.currentIndex].value)
                }
                CutButton {
                    text: root.windowRef.tr("Исходное назначение")
                    enabled: root.selected.writable && !root.controller.busy
                    onClicked: root.controller.edit("eweadn:button_bindings:"+root.controller.selectedButton,[0,0,0,0])
                }
                StyledText {
                    visible: !root.selected.writable
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                    text: root.windowRef.tr("Для этой кнопки устройство не сообщило доступный слот переназначения.")
                    color: Theme.warning; font.family: Theme.displayFont; font.pixelSize: 13
                }
                StyledText {
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                    text: root.windowRef.tr("Назначение сохраняется в черновик. Сохрани хотя бы одну кнопку с левым щелчком.")
                    color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
                }
                CutButton { text: root.windowRef.tr("Библиотека макросов"); onClicked: macros.show() }
            }
        }
    }
    RowLayout {
        visible: root.ready && root.controller.section==="pointer"
        Layout.fillWidth: true
        StyledText { text: root.windowRef.tr("Количество ступеней DPI"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 16; Layout.fillWidth: true; wrapMode: Text.Wrap }
        CutCombo {
            model: ["1","2","3","4","5","6","7","8"]
            currentIndex: (root.controller.eweadnFields["eweadn:dpi_config:count"] || {value:1}).value-1
            enabled: !root.controller.busy
            onActivated: index=>root.controller.edit("eweadn:dpi_config:count",index+1)
            Layout.preferredWidth: 100
        }
    }
    GridLayout {
        visible: root.ready && root.controller.section==="pointer"
        Layout.fillWidth: true
        columns: width>=800 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
        Repeater {
            model: root.controller.eweadnDpiModel
            delegate: CutCard {
                id: stage
                required property var capability
                readonly property var modelData: capability
                Layout.fillWidth: true; Layout.preferredWidth: 370; Layout.alignment: Qt.AlignTop
                lineColor: modelData.active ? Theme.accent : Theme.border
                implicitHeight: dpiFields.implicitHeight+32
                ColumnLayout {
                    id: dpiFields
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    spacing: 6
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle {
                            width: 18; height: 18; radius: 9; border.color: Theme.borderStrong
                            color: stage.modelData.color ? Qt.rgba(stage.modelData.color.value[0]/255,stage.modelData.color.value[1]/255,stage.modelData.color.value[2]/255,1) : Theme.muted
                            MouseArea {
                                anchors.fill: parent
                                onClicked: root.openStageColor(stage.modelData.index)
                            }
                        }
                        StyledText { text: "DPI "+(stage.modelData.index+1); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 15; Layout.fillWidth: true }
                        CutButton { text: stage.modelData.active ? "✓" : root.windowRef.tr("Выбрать"); selected: stage.modelData.active; onClicked: root.controller.edit("eweadn:dpi_config:active",stage.modelData.index) }
                    }
                    ControlEditor { visible: !!stage.modelData.x; field: stage.modelData.x; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
                    ControlEditor { visible: !!stage.modelData.y; field: stage.modelData.y; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
                    CutButton {
                        text: root.windowRef.tr("Выбрать цвет")
                        enabled: !root.controller.busy
                        onClicked: root.openStageColor(stage.modelData.index)
                    }
                }
            }
        }
    }
    GridLayout {
        visible: root.ready && ["advanced","performance"].includes(root.controller.section)
        Layout.fillWidth: true
        columns: width>=800 ? 2 : 1; columnSpacing: 12; rowSpacing: 12
        Repeater {
            model: ["advanced","performance"].includes(root.controller.section) ? root.controller.fieldModel : []
            delegate: ControlEditor {
                required property var capability
                field: capability; controller: root.controller; windowRef: root.windowRef
                Layout.fillWidth: true; Layout.preferredWidth: 370; Layout.alignment: Qt.AlignTop
            }
        }
    }
    StyledText {
        visible: root.ready && root.controller.section==="performance"
        text: root.windowRef.tr("В проводном режиме режим сенсора задаётся прошивкой. Оценка оставшегося времени работы не вычисляется без достоверных данных устройства.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true
    }
    ColumnLayout {
        visible: root.controller.section==="macros"; Layout.fillWidth: true; spacing: 12
        StyledText { text: root.windowRef.tr("Библиотека макросов"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 20 }
        CutButton { text: root.windowRef.tr("Запись и редактирование"); onClicked: macros.show() }
        StyledText {
            text: root.windowRef.tr("Запись клавиш, щелчков и пауз сохраняется локально. Загрузка в S9 требует форматирования аппаратной области макросов через OTA; безопасное чтение и восстановление этой области пока не подтверждены.")
            color: Theme.warning; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
    }
    CutCard {
        visible: root.ready && root.controller.section==="other"; Layout.fillWidth: true
        implicitHeight: other.implicitHeight+32
        ColumnLayout {
            id: other
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 12
            StyledText { text: root.controller.eweadnState.name || "EWEADN S9"; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 20 }
            StyledText { text: root.windowRef.tr("Версия прошивки")+": "+(root.controller.eweadnState.firmware_version || "—"); color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 14 }
            StyledText { text: root.windowRef.tr("Профиль (значение устройства)")+": "+root.controller.eweadnState.profiles; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 14 }
            StyledText {
                text: root.windowRef.tr("Прошивка приёмника не считана. Сброс всех настроек и обновление прошивки автоматически не выполняются.")
                color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 14; wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            CutButton { text: root.windowRef.tr("Сброс всех настроек"); enabled: root.ready && !root.controller.busy && root.controller.available; onClicked: { resetDialog.context=root.controller.eweadnContext;resetDialog.open() } }
            CutButton { text: root.windowRef.tr("Изображение карточки"); onClicked: root.chooseArtwork() }
        }
    }
}
