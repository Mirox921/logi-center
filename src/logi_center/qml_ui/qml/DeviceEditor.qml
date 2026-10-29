pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var bridge
    required property var windowRef
    signal chooseArtwork()
    readonly property var controller: bridge.editor
    readonly property bool g515Page: controller.g515Editor && ["lighting","freestyle","animations","assignments","keyboard_settings"].includes(controller.section)
    property var scrollPositions: ({})
    property string scrollKey: ""
    Connections {
        target: root.controller
        function onChanged() {
            const key=root.bridge.selectedDeviceId+"/"+root.controller.section
            if (key === root.scrollKey) return
            if (root.scrollKey.length>0) root.scrollPositions[root.scrollKey]=scroll.contentItem.contentY
            root.scrollKey=key
            Qt.callLater(function() { scroll.contentItem.contentY=root.scrollPositions[key] || 0 })
        }
    }
    spacing: 10
    ColumnLayout {
        visible: root.controller.g502Editor && root.controller.ratbagProfileStatus.profile!==undefined && root.controller.ratbagProfileStatus.profile!==null
        Layout.fillWidth: true
        StyledText {
            Layout.fillWidth: true; wrapMode: Text.Wrap
            text: root.windowRef.tr(root.controller.ratbagProfileStatus.live ? "Аппаратный профиль" : "Профиль по кэшу ratbagd")+": "+(Number(root.controller.ratbagProfileStatus.profile)+1)+
                  (root.controller.ratbagProfileStatus.mismatch ? " · "+root.windowRef.tr("ratbagd сообщает другой профиль") : "")
            color: root.controller.ratbagProfileStatus.mismatch ? Theme.warning : Theme.muted; font.family: Theme.dataFont; font.pixelSize: 13
        }
        RowLayout {
            visible: root.controller.ratbagProfileStatus.mismatch
            Layout.fillWidth: true
            StyledText { Layout.fillWidth: true; wrapMode: Text.Wrap; text: root.windowRef.tr("Показаны настройки аппаратного профиля. Перед записью синхронизируй ratbagd; открытие страницы не меняет устройство."); color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13 }
            CutButton { text: root.windowRef.tr("Синхронизировать профиль"); enabled: !root.controller.busy; onClicked: root.controller.syncRatbagProfile() }
        }
    }
    RowLayout {
        Layout.fillWidth: true
        Flickable {
            Layout.fillWidth: true; Layout.preferredHeight: 38
            contentWidth: tabs.implicitWidth; contentHeight: height; clip: true
            Row {
                id: tabs
                spacing: 6
                Repeater {
                    model: root.controller.sections
                    delegate: CutButton {
                        required property var modelData
                        text: modelData.label
                        selected: root.controller.section === modelData.id
                        onClicked: root.controller.setSection(modelData.id)
                    }
                }
            }
        }
        CutButton { text: "↻"; Accessible.name: root.windowRef.tr("Прочитать настройки"); ToolTip.visible: hovered; ToolTip.text: root.windowRef.tr("Прочитать настройки"); enabled: !root.controller.busy && root.controller.available; onClicked: root.controller.reload() }
    }
    ScrollView {
        id: scroll
        objectName: "deviceEditorScroll"
        Layout.fillWidth: true; Layout.fillHeight: true
        contentWidth: availableWidth
        clip: true
        ColumnLayout {
            width: scroll.availableWidth
            spacing: 8
            StyledText {
                objectName: "editor-live-read-error"
                visible: root.controller.liveReadError.length > 0
                text: root.windowRef.tr("Автообновление настроек: ") + root.controller.liveReadError
                font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.warning
                wrapMode: Text.Wrap; Layout.fillWidth: true
            }
            KeyboardEditor { visible: root.controller.section === "keys" && !root.controller.aceEditor && !root.controller.g515Editor; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            G515Panel { visible: root.g515Page; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            EweadnPanel { visible: root.controller.eweadnEditor; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true; onChooseArtwork: root.chooseArtwork() }
            Ace68Panel { visible: root.controller.aceEditor; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            MouseButtons { visible: root.controller.section === "buttons" && !root.controller.k7Editor && !root.controller.eweadnEditor; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            K7DpiPanel { visible: root.controller.k7Editor && root.controller.section === "pointer"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            K7ButtonPanel { visible: root.controller.k7Editor && root.controller.section === "buttons"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            K7PerformancePanel { visible: root.controller.k7Editor && root.controller.section === "advanced"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            K7DockPanel { visible: root.controller.section === "dock"; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
            CutCard {
                visible: root.controller.section === "indicators"
                Layout.fillWidth: true; Layout.preferredHeight: k7Details.implicitHeight + 28
                ColumnLayout {
                    id: k7Details
                    anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                    spacing: 10
                    StyledText {
                        text: root.windowRef.tr("Индикаторы мыши")
                        font.family: Theme.displayFont; font.pixelSize: 16; color: Theme.text
                    }
                    StyledText {
                        visible: root.controller.section === "indicators"
                        text: root.windowRef.tr("Связь с мышью") + ": " + (root.controller.k7Status.link || root.windowRef.tr("Нет данных"))
                        font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
                    }
                    StyledText {
                        visible: root.controller.section === "indicators"
                        text: root.windowRef.tr("Состояние зарядки") + ": " + (root.controller.k7Status.charging || root.windowRef.tr("Нет данных"))
                        font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
                    }
                    StyledText {
                        visible: root.controller.section === "indicators"
                        text: root.windowRef.tr("Последний прочитанный профиль") + ": " + (root.controller.k7Status.profile || root.windowRef.tr("Нет данных"))
                        font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
                    }
                    StyledText {
                        visible: root.controller.section === "indicators"
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: root.windowRef.tr("Верхний LED зарядки") + ": " + root.windowRef.tr("Состояние не сообщается")
                        font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.muted
                    }
                    RowLayout {
                        visible: root.controller.section === "indicators"
                        Layout.fillWidth: true
                        spacing: 7
                        StyledText {
                            text: root.windowRef.tr("Последняя прочитанная ступень DPI") + ": " +
                                  (root.controller.k7Status.stageNumber || root.windowRef.tr("Нет данных"))
                            font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
                        }
                        Rectangle {
                            visible: !!root.controller.k7Status.stageColor
                            Layout.preferredWidth: 16; Layout.preferredHeight: 16
                            radius: 8
                            color: root.controller.k7Status.stageColor || "transparent"
                            border.color: Theme.borderStrong; border.width: 1
                        }
                        StyledText {
                            visible: !!root.controller.k7Status.stageColor
                            text: root.controller.k7Status.stageName || ""
                            font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.text
                        }
                        Item { Layout.fillWidth: true }
                    }
                    StyledText {
                        visible: root.controller.section === "indicators"
                        Layout.fillWidth: true; wrapMode: Text.Wrap
                        text: root.windowRef.tr("Цвет ступени DPI указан по руководству; состояние LED не считывается. Верхний LED: красный при зарядке, зелёный после полного заряда.")
                        font.family: Theme.dataFont; font.pixelSize: 13; color: Theme.muted
                    }
                }
            }
            GridLayout {
                id: fieldGrid
                visible: !root.controller.eweadnEditor && !root.g515Page && !root.controller.aceEditor && root.controller.section !== "dock" && !(root.controller.k7Editor && ["pointer","buttons","advanced"].includes(root.controller.section))
                Layout.fillWidth: true
                columns: width >= 760 ? 2 : 1
                columnSpacing: 10; rowSpacing: 10
                Repeater {
                    model: root.g515Page || root.controller.eweadnEditor ? [] : root.controller.fieldModel
                    delegate: ControlEditor {
                        required property var capability
                        field: capability; controller: root.controller; windowRef: root.windowRef
                        Layout.fillWidth: true; Layout.preferredWidth: 360; Layout.alignment: Qt.AlignTop
                        // A zone's mode starts a row; its speed and brightness
                        // follow together. Keep the same order in one-column UI.
                        Layout.columnSpan: fieldGrid.columns > 1 && root.controller.section === "lighting" &&
                                           capability.id.startsWith("ratbagctl:led:") &&
                                           (capability.id.endsWith(":mode") || capability.id.endsWith(":color")) ? 2 : 1
                    }
                }
            }
            EmptyState {
                visible: !root.controller.eweadnEditor && !root.controller.g515Editor && !root.controller.aceEditor && root.controller.fieldModel.count === 0 && root.controller.section !== "buttons" && root.controller.section !== "keys" && root.controller.section !== "indicators" && root.controller.section !== "dock" && !root.controller.busy
                Layout.fillWidth: true; Layout.preferredHeight: 110
                title: root.windowRef.tr("Подтверждённые настройки не обнаружены")
                detail: root.controller.message || root.windowRef.tr("Этому устройству пока не найден совместимый модуль управления.")
            }
        }
    }
    StyledText { visible: root.controller.message.length>0 && (root.controller.eweadnEditor || root.controller.g515Editor || root.controller.aceEditor || root.controller.fieldModel.count>0 || root.controller.section === "buttons" || root.controller.section === "keys" || root.controller.section === "indicators" || root.controller.section === "dock" || root.controller.busy); text: root.controller.message; color: root.controller.resultState === "error" || root.controller.resultState === "mismatch" ? Theme.error : Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true }
    RowLayout {
        Layout.fillWidth: true
        StyledText { text: root.controller.busy ? root.windowRef.tr("Выполняется…") : root.controller.dirtyCount>0 ? root.windowRef.tr(root.controller.resultState === "sent_unverified" ? "Отправлено, не подтверждено" : "Не сохранено")+": "+root.controller.dirtyCount : ""; color: Theme.warning; font.family: Theme.dataFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.minimumWidth: 0; Layout.fillWidth: true }
        CutButton { visible: root.controller.busy; text: root.windowRef.tr("Отменить"); onClicked: root.controller.cancel() }
        CutButton { visible: root.controller.dirtyCount>0 && !root.controller.busy; text: root.windowRef.tr("Отменить черновик"); onClicked: root.controller.discardGroup() }
        CutButton { objectName: "editor-apply"; visible: root.controller.dirtyCount>0 && !root.controller.busy; text: root.windowRef.tr("Применить"); primary: true; enabled: root.controller.available; onClicked: root.controller.applyGroup() }
    }
}
