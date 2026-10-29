pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    readonly property var fields: controller.k7Fields
    readonly property int count: field("count").value || 1
    readonly property int active: field("active").value || 0
    readonly property var colors: ["#d85b55","#548bd6","#59ad78","#d8b547","#50b8c4","#a77ad1"]
    function field(key) { return fields["mchose:dpi_config:"+key] || ({value:0, writable:false, dirty:false}) }
    function edit(key,value) { controller.edit("mchose:dpi_config:"+key,value) }
    function position(value) { return value<=4200 ? (value-200)/4000*.75 : .75+(value-4200)/37800*.25 }
    function dpi(position) { return Math.max(200,Math.round((position<=.75 ? 200+position/.75*4000 : 4200+(position-.75)/.25*37800)/50)*50) }
    spacing: 12
    CutCard {
        visible: root.controller.k7LegacyDrafts.length>0
        Layout.fillWidth: true; Layout.preferredHeight: legacy.implicitHeight+32
        ColumnLayout {
            id: legacy
            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
            spacing: 8
            StyledText {
                Layout.fillWidth: true; wrapMode: Text.Wrap
                text: root.windowRef.tr("Старые черновики сохранены. Проверь профиль и ступень, затем введи нужные значения в новый редактор.")
                color: Theme.warning; font.family: Theme.displayFont; font.pixelSize: 13
            }
            Repeater {
                model: root.controller.k7LegacyDrafts
                delegate: ColumnLayout {
                    required property var modelData
                    Layout.fillWidth: true
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: modelData.label+": "+modelData.value
                        color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 13
                    }
                    CutButton { text: root.windowRef.tr("Удалить старый черновик"); enabled: !root.controller.busy; onClicked: root.controller.discardK7LegacyDraft(modelData.key) }
                }
            }
        }
    }
    Flow {
        Layout.fillWidth: true
        spacing: 8
        StyledText { height: 38; verticalAlignment: Text.AlignVCenter; text: root.windowRef.tr("Количество ступеней"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 14 }
        Row {
            spacing: 4
            Repeater {
                model: 6
                delegate: CutButton {
                    required property int index
                    objectName: "k7-dpi-count-"+(index+1)
                    text: String(index+1); implicitWidth: 38
                    selected: root.count===index+1; quietSelected: true
                    enabled: root.field("count").writable && !root.controller.busy
                    onClicked: root.edit("count",index+1)
                }
            }
        }
        CutButton {
            visible: root.controller.k7AxesAvailable
            text: root.windowRef.tr("Раздельно X / Y"); selected: root.controller.k7SeparateAxes; quietSelected: true
            enabled: root.field("count").writable && !root.controller.busy
            onClicked: root.controller.setK7SeparateAxes(!root.controller.k7SeparateAxes)
        }
    }
    GridLayout {
        Layout.fillWidth: true
        columns: width>=850 ? 2 : 1
        columnSpacing: 12; rowSpacing: 12
        Repeater {
            model: 6
            delegate: CutCard {
                id: stage
                required property int index
                readonly property bool enabledStage: index<root.count
                visible: enabledStage
                objectName: "k7-dpi-stage-"+index
                Layout.fillWidth: true; Layout.preferredWidth: 410
                Layout.preferredHeight: content.implicitHeight+32
                lineColor: root.active===index ? Theme.accent : Theme.border
                ColumnLayout {
                    id: content
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Rectangle { Layout.preferredWidth: 14; Layout.preferredHeight: 14; radius: 7; color: root.colors[stage.index] }
                        StyledText { text: root.windowRef.tr("Уровень DPI")+" "+(stage.index+1); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 15; Layout.fillWidth: true }
                        CutButton {
                            objectName: "k7-dpi-activate-"+stage.index
                            text: root.active===stage.index ? root.windowRef.tr("Активная") : root.windowRef.tr("Выбрать")
                            selected: root.active===stage.index; quietSelected: true
                            enabled: root.field("active").writable && !root.controller.busy
                            onClicked: root.edit("active",stage.index)
                        }
                    }
                    Repeater {
                        model: root.controller.k7SeparateAxes ? ["x","y"] : ["x"]
                        delegate: ColumnLayout {
                            id: axis
                            required property string modelData
                            readonly property var setting: root.field(modelData+stage.index)
                            Layout.fillWidth: true; spacing: 2
                            RowLayout {
                                Layout.fillWidth: true
                                StyledText { visible: root.controller.k7SeparateAxes; text: axis.modelData.toUpperCase(); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13 }
                                CutSlider {
                                    id: sensitivity
                                    objectName: "k7-dpi-slider-"+axis.modelData+stage.index
                                    Layout.fillWidth: true; from: 0; to: 1
                                    value: root.position(axis.setting.value || 200)
                                    enabled: axis.setting.writable && !root.controller.busy
                                    onMoved: root.edit(axis.modelData+stage.index,root.dpi(value))
                                    Accessible.name: "DPI "+axis.modelData.toUpperCase()+" "+(stage.index+1)
                                }
                                NumberInput {
                                    objectName: "k7-dpi-input-"+axis.modelData+stage.index
                                    Layout.preferredWidth: 90
                                    numberValue: axis.setting.value || 200
                                    validator: IntValidator { bottom: 200; top: 42000 }
                                    enabled: axis.setting.writable && !root.controller.busy
                                    onNumberCommitted: value => root.edit(axis.modelData+stage.index,value)
                                    Accessible.name: "DPI "+axis.modelData.toUpperCase()+" "+(stage.index+1)
                                }
                            }
                            Item {
                                Layout.fillWidth: true; Layout.preferredHeight: 17
                                StyledText { x: sensitivity.x+sensitivity.leftPadding; text: "200"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                                StyledText { x: sensitivity.x+sensitivity.width*.75-width/2; text: "4200"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                                StyledText { x: sensitivity.x+sensitivity.width-width; text: "42000"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                            }
                        }
                    }
                    StyledText {
                        visible: root.field("x"+stage.index).dirty || root.field("y"+stage.index).dirty
                        text: root.windowRef.tr("Не сохранено"); color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 12
                    }
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Цвета ступеней — по руководству K7. Изменения DPI отправляются вместе после «Применить».")
        color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12
    }
    Loader {
        active: !!root.fields["mchose:polling_rate"]
        Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
        sourceComponent: ControlEditor {
            field: root.fields["mchose:polling_rate"]
            controller: root.controller; windowRef: root.windowRef
        }
    }
}
