pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

FocusScope {
    id: root
    required property var controller
    required property var windowRef
    implicitHeight: content.implicitHeight
    function keyName(event) {
        const names={}
        names[Qt.Key_Control]="Control_L"; names[Qt.Key_Shift]="Shift_L"; names[Qt.Key_Alt]="Alt_L"; names[Qt.Key_Meta]="Super_L"
        names[Qt.Key_Return]="Return"; names[Qt.Key_Escape]="Escape"; names[Qt.Key_Space]="space"; names[Qt.Key_Tab]="Tab"; names[Qt.Key_Backspace]="BackSpace"
        names[Qt.Key_Left]="Left"; names[Qt.Key_Right]="Right"; names[Qt.Key_Up]="Up"; names[Qt.Key_Down]="Down"; names[Qt.Key_Delete]="Delete"
        if (event.key >= Qt.Key_F1 && event.key <= Qt.Key_F24) return "F"+(event.key-Qt.Key_F1+1)
        if (event.key >= Qt.Key_A && event.key <= Qt.Key_Z) return String.fromCharCode(event.key)
        if (event.key >= Qt.Key_0 && event.key <= Qt.Key_9) return String.fromCharCode(event.key)
        return names[event.key] || event.text
    }
    Keys.onPressed: event => { if (root.controller.recording) { if (!event.isAutoRepeat) root.controller.recordKey(root.keyName(event),true); event.accepted=true } }
    Keys.onReleased: event => { if (root.controller.recording) { if (!event.isAutoRepeat) root.controller.recordKey(root.keyName(event),false); event.accepted=true } }
    onActiveFocusChanged: { if (!activeFocus) root.controller.stopRecording() }
    onVisibleChanged: { if (!visible) root.controller.stopRecording() }
    ColumnLayout {
        id: content
        width: root.width
        spacing: 10
        GridLayout {
            Layout.fillWidth: true
            columns: width >= 780 ? 2 : 1
            columnSpacing: 18
            rowSpacing: 10
            Item {
                id: diagram
                objectName: "mouse-button-diagram"
                Layout.fillWidth: true
                Layout.preferredWidth: 400
                Layout.preferredHeight: 300
                readonly property real fit: Math.min(width/480,height/440)
                readonly property real offsetX: (width-480*fit)/2
                readonly property real offsetY: (height-440*fit)/2
                Image {
                    objectName: "mouse-button-artwork"
                    x: diagram.offsetX; y: diagram.offsetY
                    width: 480*diagram.fit; height: 440*diagram.fit
                    source: Qt.resolvedUrl(root.controller.buttonDiagram)
                    fillMode: Image.PreserveAspectFit
                }
                Canvas {
                    id: leaders
                    anchors.fill: parent
                    onWidthChanged: requestPaint()
                    onHeightChanged: requestPaint()
                    Connections { target: root.controller; function onChanged() { leaders.requestPaint() } }
                    onPaint: {
                        const ctx=getContext("2d")
                        ctx.clearRect(0,0,width,height)
                        for (const b of root.controller.buttons) {
                            const ax=diagram.offsetX+b.x*480*diagram.fit
                            const ay=diagram.offsetY+b.y*440*diagram.fit
                            const selected=b.index === root.controller.selectedButton
                            ctx.fillStyle=selected ? Theme.accent : Theme.muted
                            ctx.beginPath(); ctx.arc(ax,ay,selected ? 4 : 2,0,2*Math.PI); ctx.fill()
                            if (!selected) continue
                            const cx=diagram.offsetX+b.cx*480*diagram.fit
                            const cy=diagram.offsetY+b.cy*440*diagram.fit
                            const direction=cx < width/2 ? 1 : -1
                            ctx.strokeStyle=Theme.accent; ctx.lineWidth=1
                            ctx.beginPath(); ctx.moveTo(cx+direction*18,cy)
                            ctx.lineTo(cx+direction*30,cy); ctx.lineTo(ax,ay); ctx.stroke()
                        }
                    }
                }
                Repeater {
                    model: root.controller.buttons
                    delegate: CutButton {
                        required property var modelData
                        objectName: "mouse-button-callout-"+modelData.index
                        x: Math.round(diagram.offsetX+modelData.cx*480*diagram.fit)-22
                        y: Math.round(diagram.offsetY+modelData.cy*440*diagram.fit)-16
                        id: callout
                        width: 44; height: 32
                        text: String(modelData.index+1)
                        contentItem: StyledText {
                            text: callout.text
                            color: callout.selected ? Theme.accent : Theme.text
                            font.family: Theme.dataFont; font.pixelSize: 12
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        selected: root.controller.selectedButton === modelData.index
                        Accessible.name: modelData.label
                        ToolTip.visible: hovered; ToolTip.text: modelData.label
                        onClicked: root.controller.selectButton(modelData.index)
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.preferredWidth: 360
                spacing: 8
                StyledText { text: root.windowRef.tr("Кнопки и макросы"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 19 }
                CutCombo {
                    objectName: "mouse-button-selector"
                    Layout.fillWidth: true
                    model: root.controller.buttons; textRole: "label"
                    currentIndex: root.controller.buttons.findIndex(b=>b.index===root.controller.selectedButton)
                    onActivated: index=>root.controller.selectButton(root.controller.buttons[index].index)
                }
                StyledText { text: root.windowRef.tr("Сейчас: ")+root.controller.currentAssignment; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.Wrap }
                CutCombo { id: assignment; Layout.fillWidth: true; model: root.controller.assignments; textRole: "label"; currentIndex: root.controller.assignmentIndex; onActivated: index=>root.controller.chooseAssignment(index) }
                CutButton { text: root.windowRef.tr("Применить назначение"); enabled: !root.controller.busy && root.controller.available && assignment.count>0 && assignment.currentIndex>=0; onClicked: root.controller.applyAssignment(assignment.currentIndex) }
                StyledText { text: root.windowRef.tr("Макрос"); font.family: Theme.displayFont; font.pixelSize: 19; color: Theme.text }
                StyledText { text: root.windowRef.tr("Нажимай клавиши в этом окне. Системные сочетания могут перехватываться рабочим столом."); color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
                Flow {
                    Layout.fillWidth: true; spacing: 6
                    CutButton { text: root.controller.recording ? root.windowRef.tr("Остановить запись клавиш") : root.windowRef.tr("Записать клавиши"); selected: root.controller.recording; enabled: root.controller.macroSupported && !root.controller.busy; onClicked: { root.controller.setRecording(!root.controller.recording); if (root.controller.recording) root.forceActiveFocus() } }
                    CutInput { id: delay; text: "100"; width: 64; placeholderText: "ms" }
                    CutButton { text: root.windowRef.tr("Добавить паузу"); enabled: root.controller.macroSupported; onClicked: root.controller.addPause(Number(delay.text)) }
                    CutButton { text: root.windowRef.tr("Очистить"); onClicked: root.controller.clearMacro() }
                }
            }
        }
        StyledText { text: root.windowRef.tr("Схема расположения кнопок · не отображает текущий цвет подсветки"); color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
        Repeater {
            model: root.controller.macroEvents
            delegate: RowLayout {
                required property var modelData
                Layout.fillWidth: true
                StyledText { text: modelData.label; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13; Layout.fillWidth: true }
                CutButton { text: "×"; Accessible.name: root.windowRef.tr("Удалить"); onClicked: root.controller.removeEvent(modelData.index) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            CutButton { text: root.windowRef.tr("Отменить черновик"); onClicked: root.controller.resetMacro() }
            Item { Layout.fillWidth: true }
            CutButton { text: root.windowRef.tr("Применить макрос"); primary: true; enabled: root.controller.macroSupported && !root.controller.busy && root.controller.available && !root.controller.macroConflict; onClicked: root.controller.applyMacro() }
        }
    }
}
