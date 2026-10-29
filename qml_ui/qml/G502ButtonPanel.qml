pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    objectName: "g502-button-panel"
    required property var controller
    required property var windowRef
    property string category: "mouse"
    readonly property bool wide: width>=950
    readonly property bool sideView: controller.g502View==="side"
    readonly property var macroWindow: macros
    function openMacros() { macros.show() }
    function group(action) {
        if (action[0]==="macro") return "shortcuts"
        if (action[0]==="key") return /VOLUME|MUTE|PLAY|SONG/.test(action[1]) ? "media" : "keyboard"
        return "mouse"
    }
    spacing: 12
    MacroWindow { id: macros; controller: root.controller; windowRef: root.windowRef }
    GridLayout {
        Layout.fillWidth: true; columns: root.wide ? 2 : 1; columnSpacing: 14; rowSpacing: 12
        CutCard {
            Layout.row: root.wide ? 0 : 1; Layout.column: 0
            Layout.preferredWidth: root.wide ? 270 : -1; Layout.fillWidth: !root.wide
            Layout.preferredHeight: library.implicitHeight+32
            ColumnLayout {
                id: library
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                spacing: 8
                StyledText { text: root.windowRef.tr("Назначение кнопки"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 17 }
                CutInput { id: search; Layout.fillWidth: true; placeholderText: root.windowRef.tr("Поиск действия"); Accessible.name: placeholderText }
                Flow {
                    Layout.fillWidth: true; spacing: 5
                    Repeater {
                        model: [{id:"mouse",label:root.windowRef.tr("Мышь / DPI")},{id:"keyboard",label:root.windowRef.tr("Клавиатура")},{id:"shortcuts",label:root.windowRef.tr("Сочетания")},{id:"media",label:root.windowRef.tr("Мультимедиа")}].filter(tab=>tab.id!=="media" || root.controller.assignments.some(action=>root.group(action.value)==="media"))
                        delegate: CutButton {
                            required property var modelData
                            text: modelData.label; selected: root.category===modelData.id; quietSelected: true
                            onClicked: root.category=modelData.id
                        }
                    }
                }
                Repeater {
                    model: root.controller.assignments
                    delegate: CutButton {
                        required property int index
                        required property var modelData
                        visible: root.group(modelData.value)===root.category && (search.text.length===0 || modelData.label.toLowerCase().includes(search.text.toLowerCase()))
                        Layout.fillWidth: true; text: modelData.label
                        selected: root.controller.assignmentIndex===index; quietSelected: true
                        enabled: !root.controller.busy
                        onClicked: root.controller.chooseAssignment(index)
                    }
                }
                CutButton {
                    text: root.windowRef.tr("Библиотека макросов"); Layout.fillWidth: true
                    objectName: "macro-library-open"
                    enabled: root.controller.macroSupported && !root.controller.busy
                    onClicked: macros.show()
                }
            }
        }
        CutCard {
            Layout.row: 0; Layout.column: root.wide ? 1 : 0
            Layout.fillWidth: true; Layout.preferredHeight: content.implicitHeight+32
            ColumnLayout {
                id: content
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    StyledText { text: root.controller.deviceName; color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 17; Layout.fillWidth: true; elide: Text.ElideRight }
                    CutButton { objectName: "g502-view-top"; text: root.windowRef.tr("Сверху"); selected: !root.sideView; quietSelected: true; onClicked: root.controller.setG502View("top") }
                    CutButton { objectName: "g502-view-side"; text: root.windowRef.tr("Сбоку"); selected: root.sideView; quietSelected: true; onClicked: root.controller.setG502View("side") }
                }
                Item {
                    id: diagram
                    objectName: "g502-button-diagram"
                    clip: true
                    Layout.fillWidth: true; Layout.preferredHeight: 440
                    function labelX(button) {
                        if (root.sideView) return button.index===3 ? width-labelWidth : 0
                        return button.side==="right" ? width-labelWidth : 0
                    }
                    function labelY(button) { return root.sideView ? button.index===5 ? height-42 : 12 : 28+button.row*94 }
                    function route(button) {
                        const ax=mouse.x+button.x*mouse.width, ay=mouse.y+button.y*mouse.height
                        const lx=labelX(button), ly=labelY(button)+17
                        const right=lx>width/2, end=right ? lx : lx+labelWidth
                        let points
                        if (root.sideView) {
                            const lane=button.index===5 ? mouse.y+mouse.height+12 : mouse.y-12
                            const elbow=end+(right ? -12 : 12)
                            points=[{x:ax,y:ay},{x:ax,y:lane},{x:elbow,y:lane},{x:elbow,y:ly},{x:end,y:ly}]
                        } else {
                            const edge=right ? mouse.x+mouse.width : mouse.x
                            const gap=Math.abs(end-edge), inset=Math.min(10,gap/3)
                            const step=Math.min(7,Math.max(0,gap-2*inset)/3)
                            const gutter=edge+(right ? 1 : -1)*(inset+(3-button.row)*step)
                            // Separate wheel-press / tilt stems without moving
                            // their physical anchors or their original hitboxes.
                            const lowerDpi=root.controller.g502Buttons.find(b=>b.index===6)
                            const lowerLane=lowerDpi ? mouse.y+lowerDpi.y*mouse.height+14 : ay+26
                            const escape=button.index===2 ? ay-14 : button.index===10 ? Math.max(ay+26,lowerLane) : ay
                            points=[{x:ax,y:ay},{x:ax,y:escape},{x:gutter,y:escape},{x:gutter,y:ly},{x:end,y:ly}]
                        }
                        return points.map(p=>({x:Math.max(2,Math.min(width-2,p.x)),y:Math.max(2,Math.min(height-2,p.y))}))
                    }
                    readonly property real labelWidth: Math.min(156,width*.28)
                    Image {
                        id: mouse
                        objectName: "g502-button-artwork"
                        readonly property bool artworkReady: status===Image.Ready
                        anchors.centerIn: parent
                        readonly property real aspect: root.controller.g502Canvas.width/root.controller.g502Canvas.height
                        width: root.sideView ? Math.min(parent.width-12,700) : height*aspect
                        height: root.sideView ? width/aspect : Math.min(410,(parent.width-12)/aspect)
                        // Hidden copies must not rasterize another device's generic SVG.
                        source: root.visible && root.controller.g502Editor && width>1 && height>1 ? Qt.resolvedUrl(root.controller.buttonDiagram) : ""
                        // The viewBox is geometry, not a texture-size budget. Let
                        // the decoder derive height from the actual SVG: during
                        // top/side transitions its aspect may differ from layout.
                        sourceSize.width: Math.max(8,Math.min(1024,Math.ceil(width*Screen.devicePixelRatio)))
                        sourceSize.height: -1
                        fillMode: Image.PreserveAspectFit
                    }
                    Canvas {
                        id: leaders
                        anchors.fill: parent
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        Connections { target: root.controller; function onChanged() { leaders.requestPaint() } }
                        onPaint: {
                            const ctx=getContext("2d");ctx.reset();ctx.lineCap="round";ctx.lineJoin="round"
                            for (let i=0;i<targets.count;i++) {
                                const target=targets.itemAt(i)
                                if (!target || target.lineAlpha<=0) continue
                                const points=target.routePoints
                                ctx.globalAlpha=target.lineAlpha
                                ctx.lineWidth=target.chosen ? 1.4 : 1
                                ctx.strokeStyle=target.chosen ? Theme.accent : Theme.text
                                ctx.beginPath();ctx.moveTo(points[0].x,points[0].y)
                                for (let j=1;j<points.length;j++) ctx.lineTo(points[j].x,points[j].y)
                                ctx.stroke()
                            }
                        }
                    }
                    Repeater {
                        id: targets
                        model: root.controller.g502Buttons
                        delegate: Item {
                            id: target
                            objectName: "g502-button-overlay-"+modelData.index
                            required property var modelData
                            readonly property bool chosen: modelData.index===root.controller.selectedButton
                            readonly property bool hoverActive: label.hovered || markerMouse.containsMouse
                            readonly property var routePoints: diagram.route(modelData)
                            property real lineAlpha: chosen ? 1 : hoverActive ? .78 : 0
                            onLineAlphaChanged: leaders.requestPaint()
                            onRoutePointsChanged: leaders.requestPaint()
                            Behavior on lineAlpha { NumberAnimation { duration: Theme.motion } }
                            anchors.fill: parent
                            CutButton {
                                id: label
                                objectName: "g502-button-label-"+target.modelData.index
                                x: diagram.labelX(target.modelData); y: diagram.labelY(target.modelData)
                                width: diagram.labelWidth; text: target.modelData.label
                                selected: target.chosen; quietSelected: true
                                onClicked: root.controller.selectButton(target.modelData.index)
                            }
                            Item {
                                id: hitbox
                                objectName: "g502-button-anchor-"+target.modelData.index
                                x: mouse.x+target.modelData.x*mouse.width-width/2; y: mouse.y+target.modelData.y*mouse.height-height/2
                                // Interaction geometry stays 12×12 at the same
                                // anchor; only the visible dot becomes smaller.
                                width: 12; height: 12
                                Rectangle {
                                    objectName: "g502-button-dot-"+target.modelData.index
                                    anchors.centerIn: parent
                                    width: target.chosen ? 9 : target.hoverActive ? 7 : 4
                                    height: width; radius: width/2
                                    color: target.chosen ? Theme.accent : target.hoverActive ? Theme.text : Theme.muted
                                    opacity: target.chosen || target.hoverActive ? 1 : .38
                                    Behavior on width { NumberAnimation { duration: Theme.motion } }
                                    Behavior on color { ColorAnimation { duration: Theme.motion } }
                                    Behavior on opacity { NumberAnimation { duration: Theme.motion } }
                                }
                                ToolTip {
                                    id: buttonTip
                                    objectName: "g502-button-tooltip-"+target.modelData.index
                                    parent: hitbox
                                    visible: target.hoverActive; delay: 300
                                    text: target.modelData.label
                                    horizontalPadding: 8; verticalPadding: 6
                                    contentItem: StyledText { text: buttonTip.text; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12 }
                                    background: Rectangle { color: Theme.surface2; border.color: Theme.borderStrong; radius: 2 }
                                }
                                MouseArea {
                                    id: markerMouse
                                    anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                    onClicked: root.controller.selectButton(target.modelData.index)
                                }
                            }
                        }
                    }
                }
                CutCombo {
                    Layout.fillWidth: true; model: root.controller.g502Buttons; textRole: "label"
                    currentIndex: root.controller.g502Buttons.findIndex(b=>b.index===root.controller.selectedButton)
                    onActivated: index=>root.controller.selectButton(root.controller.g502Buttons[index].index)
                }
                StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.windowRef.tr("Сейчас: ")+root.controller.currentAssignment; color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13 }
                RowLayout {
                    Layout.fillWidth: true
                    CutButton { text: root.windowRef.tr("Отменить черновик"); enabled: !root.controller.busy; onClicked: root.controller.resetMacro() }
                    Item { Layout.fillWidth: true }
                    CutButton { text: root.windowRef.tr("Применить назначение"); primary: true; enabled: !root.controller.busy && root.controller.available && root.controller.assignmentIndex>=0; onClicked: root.controller.applyAssignment(root.controller.assignmentIndex) }
                }
                StyledText {
                    Layout.fillWidth: true; wrapMode: Text.Wrap
                    text: root.windowRef.tr("Верхние и боковые кнопки показаны отдельно. Механическая разблокировка колеса не переназначается.")
                    color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
                }
            }
        }
    }
}
