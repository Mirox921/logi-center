pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    objectName: "ace-advanced-panel"
    required property var controller
    required property var windowRef
    property string kind: "rs"
    property string context: controller.aceContext
    property var editing: null
    property var values: [[16,0,4],[16,0,7],[16,0,22],[16,0,26]]
    property var phases: [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    property int duration: 200
    property int priority: 0
    readonly property var actions: controller.aceActions.filter(a => a.group==="basic" && a.value[0]===16)
    readonly property int actionCount: kind==="dks" ? 4 : kind==="tgl" ? 1 : 2
    onContextChanged: { editing=null; duration=200; priority=0 }
    Connections {
        target: root.controller
        function onChanged() {
            if (root.editing && JSON.stringify(root.editing.keys.slice().sort((a,b)=>a-b))!==JSON.stringify(root.controller.aceSelectedKeys.map(k=>Number(k)).sort((a,b)=>a-b))) root.editing=null
        }
    }
    function stage() {
        const keys=controller.aceSelectedKeys.map(k => Number(k)).sort((a,b)=>a-b)
        let spec={kind:kind,layer:controller.aceLayer,keys:keys,actions:values.slice(0,actionCount)}
        if (kind==="mt") spec.time=duration
        if (kind==="socd") spec.priority=priority
        if (kind==="dks") { spec.points=editing && editing.points ? editing.points : [10,30,30,10]; spec.phases=phases }
        controller.stageAceAdvanced(spec,context)
    }
    function load(spec) {
        if (!spec) return
        controller.setAceLayer(spec.layer)
        controller.selectAceKeys("none")
        for (const key of spec.keys) controller.toggleAceKey(String(key))
        editing=spec; kind=spec.kind
        values=spec.actions.concat([[16,0,4],[16,0,7],[16,0,22],[16,0,26]]).slice(0,4)
        duration=spec.time===undefined ? 200 : spec.time
        priority=spec.priority===undefined ? 0 : spec.priority
        phases=spec.phases || [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    }
    spacing: 12
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
        CutButton { text: root.windowRef.tr("Прочитать расширенные привязки"); enabled: !root.controller.busy; onClicked: root.controller.readAceAdvanced() }
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("RS и SOCD: выбери две клавиши. DKS, MT и TGL: одну. Привязки выполняются прошивкой; программа не эмулирует нажатия.")
        font.family: Theme.displayFont; font.pixelSize: 14; color: Theme.muted
    }
    Flow {
        Layout.fillWidth: true; spacing: 6
        Repeater {
            model: ["rs","socd","dks","mt","tgl"]
            delegate: CutButton {
                required property string modelData
                text: modelData.toUpperCase(); selected: root.kind===modelData; quietSelected: true
                onClicked: { root.kind=modelData; root.editing=null }
            }
        }
        CutButton { text: root.windowRef.tr("Новая привязка"); onClicked: root.editing=null }
    }
    GridLayout {
        Layout.fillWidth: true; columns: width>=850 ? 2 : 1; columnSpacing: 12; rowSpacing: 10
        Repeater {
            model: root.actionCount
            delegate: ColumnLayout {
                id: actionRow
                required property int index
                Layout.fillWidth: true
                StyledText {
                    text: root.kind==="mt" ? root.windowRef.tr(actionRow.index===0 ? "Короткое нажатие" : "Удержание") : root.windowRef.tr("Действие")+" "+(actionRow.index+1)
                    font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.text
                }
                CutCombo {
                    Layout.fillWidth: true; model: root.actions; textRole: "label"
                    currentIndex: root.actions.findIndex(a => JSON.stringify(a.value)===JSON.stringify(root.values[actionRow.index]))
                    onActivated: i => { let v=root.values.slice(); v[actionRow.index]=root.actions[i].value; root.values=v }
                }
                Flow {
                    visible: root.kind==="dks"; Layout.fillWidth: true; spacing: 6
                    Repeater {
                        model: [root.windowRef.tr("Начало нажатия"),root.windowRef.tr("Конец нажатия"),root.windowRef.tr("Начало отпускания"),root.windowRef.tr("Конец отпускания")]
                        delegate: Column {
                            id: phase
                            required property int index
                            required property string modelData
                            spacing: 4
                            StyledText { text: phase.modelData; color: Theme.muted; font.pixelSize: 13 }
                            CutCombo {
                                model: phase.index===0 ? [0,1,2,3,4] : phase.index===1 ? [0,1,2,3] : phase.index===2 ? [0,1,2] : [0,1]
                                currentIndex: root.phases[actionRow.index][phase.index]
                                onActivated: i => { let p=JSON.parse(JSON.stringify(root.phases)); p[actionRow.index][phase.index]=i; root.phases=p }
                            }
                        }
                    }
                }
            }
        }
    }
    RowLayout {
        visible: root.kind==="mt"
        StyledText { text: root.windowRef.tr("Порог удержания, мс"); color: Theme.text; font.pixelSize: 14 }
        NumberInput {
            Layout.preferredWidth: 120; numberValue: root.duration
            validator: IntValidator { bottom: 0; top: 1000 }
            onNumberCommitted: value => root.duration=Math.round(value/10)*10
        }
    }
    RowLayout {
        visible: root.kind==="socd"
        StyledText { text: root.windowRef.tr("Приоритет SOCD"); color: Theme.text; font.pixelSize: 14 }
        CutCombo {
            model: [root.windowRef.tr("Последняя нажатая"),root.windowRef.tr("Первая клавиша пары"),root.windowRef.tr("Вторая клавиша пары"),root.windowRef.tr("Взаимная отмена")]
            currentIndex: root.priority; onActivated: i => root.priority=i
        }
    }
    StyledText {
        visible: root.kind==="dks" || root.kind==="socd"
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Коды фаз и приоритета соответствуют M HUB. Пороговые точки DKS сохраняются; неподтверждённые миллиметры не подставляются.")
        font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.subtle
    }
    CutButton {
        objectName: "ace-advanced-stage"
        text: root.windowRef.tr("Добавить в черновик")
        enabled: root.controller.aceAdvancedReady && !root.controller.busy
        onClicked: root.stage()
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Запись — только после «Применить», по одной привязке. Изменения остальных клавиш и слоёв сохраняются. Физическая работа новых привязок пока не проверена.")
        font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.muted
    }
    Repeater {
        model: root.controller.aceAdvancedBindings
        delegate: RowLayout {
            required property var modelData
            Layout.fillWidth: true
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: (modelData.spec || modelData.observed) ? (modelData.spec || modelData.observed).kind.toUpperCase()+" · "+["Windows","Windows Fn","Mac","Mac Fn"][(modelData.spec || modelData.observed).layer]+" · "+(modelData.spec || modelData.observed).keys.map(k => { const key=root.controller.keyModel.find(row => row.id===String(k)); return key ? key.label : "?" }).join(" + ")+(modelData.dirty ? " *" : "") : "—"
                color: modelData.conflict ? Theme.accent : Theme.text; font.pixelSize: 14
            }
            CutButton { text: root.windowRef.tr("Редактировать"); enabled: !root.controller.busy; onClicked: root.load(modelData.spec || modelData.observed) }
            CutButton { text: root.windowRef.tr("Удалить"); enabled: !root.controller.busy; onClicked: root.controller.removeAceAdvanced(modelData.id,root.context) }
        }
    }
    CutCard {
        Layout.fillWidth: true; Layout.preferredHeight: testContent.implicitHeight+32
        ColumnLayout {
            id: testContent
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 8
            StyledText { text: root.windowRef.tr("Проверка нажатий"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 15 }
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Тест получает обычные события клавиш только в этой области. Ход магнитного переключателя не измеряется. Esc завершает тест.")
                color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
            }
            CutButton { objectName: "ace-key-test-start"; text: root.windowRef.tr("Начать проверку клавиш"); onClicked: testArea.forceActiveFocus() }
            Rectangle {
                id: testArea
                objectName: "ace-key-test-area"
                property var pressed: ({})
                Layout.fillWidth: true; Layout.preferredHeight: 52
                color: Theme.background; border.width: 1; border.color: activeFocus ? Theme.accent : Theme.borderStrong
                onActiveFocusChanged: { if (!activeFocus) pressed=({}) }
                onVisibleChanged: { if (!visible) focus=false }
                Keys.onShortcutOverride: event => event.accepted=true
                Keys.onPressed: event => {
                    event.accepted=true
                    if (event.key===Qt.Key_Escape) { focus=false; return }
                    if (event.isAutoRepeat) return
                    const names=({[Qt.Key_Control]:"Ctrl",[Qt.Key_Shift]:"Shift",[Qt.Key_Alt]:"Alt",[Qt.Key_Meta]:"Super",[Qt.Key_Tab]:"Tab",[Qt.Key_Return]:"Enter",[Qt.Key_Enter]:"Enter",[Qt.Key_Backspace]:"Backspace",[Qt.Key_Space]:"Space"})
                    let next=Object.assign({},pressed); next[event.key]=names[event.key] || (event.text && event.text.trim().length ? event.text.toUpperCase() : "Key "+event.key); pressed=next
                }
                Keys.onReleased: event => {
                    event.accepted=true
                    if (event.isAutoRepeat) return
                    let next=Object.assign({},pressed); delete next[event.key]; pressed=next
                }
                StyledText {
                    anchors.fill: parent; anchors.margins: 10; verticalAlignment: Text.AlignVCenter
                    text: testArea.activeFocus ? Object.values(testArea.pressed).join(" + ") || root.windowRef.tr("Нажми клавишу…") : root.windowRef.tr("Проверка остановлена")
                    color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 14
                    elide: Text.ElideRight
                }
            }
        }
    }
}
