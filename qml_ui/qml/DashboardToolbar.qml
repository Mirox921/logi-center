pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

Item {
    id: toolbar
    required property var bridge
    required property var windowRef
    implicitHeight: 42
    z: 3
    Rectangle { objectName: "dashboardPanelSurface"; anchors.fill: parent; z: -1; color: Theme.background }
    property bool wide: width >= 924
    function focusSearch() {
        if (wide) { inlineSearch.forceActiveFocus(); inlineSearch.selectAll() }
        else searchPopup.open()
    }
    Shortcut { sequence: "Ctrl+K"; enabled: toolbar.windowRef.page === "dashboard"; onActivated: toolbar.focusSearch() }
    Shortcut { sequence: "/"; enabled: toolbar.windowRef.page === "dashboard" && !inlineSearch.activeFocus && !compactSearch.activeFocus; onActivated: toolbar.focusSearch() }
    RowLayout {
        anchors.fill: parent; spacing: 8
        Flickable {
            id: tabsViewport
            objectName: "categoryTabs"
            Layout.fillWidth: true; Layout.fillHeight: true
            contentWidth: tabs.width; contentHeight: height
            flickableDirection: Flickable.HorizontalFlick
            clip: true; boundsBehavior: Flickable.StopAtBounds
            Row {
                id: tabs
                height: tabsViewport.height; spacing: 4
                Repeater {
                    model: [{key:"all",label:"Все"},{key:"mouse",label:"Мыши"},{key:"keyboard",label:"Клавиатуры"},{key:"audio",label:"Аудио"}]
                    delegate: Button {
                        id: tab
                        required property var modelData
                        objectName: "category-" + modelData.key
                        readonly property bool selected: toolbar.windowRef.categoryFilter === modelData.key
                        text: toolbar.windowRef.tr(modelData.label)
                        implicitHeight: 42; implicitWidth: tabContent.implicitWidth + 18
                        hoverEnabled: true
                        onClicked: toolbar.bridge.setCategory(modelData.key)
                        Accessible.role: Accessible.RadioButton
                        Accessible.checked: selected
                        Accessible.name: text + " " + (toolbar.bridge.categoryCounts[modelData.key] || 0)
                        background: Rectangle {
                            color: tab.hovered ? Theme.surface1 : "transparent"
                            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: tab.selected ? 2 : 1; color: tab.selected || tab.activeFocus ? Theme.accent : "transparent" }
                        }
                        contentItem: RowLayout {
                            id: tabContent
                            spacing: 6
                            StyledText { text: tab.text; color: tab.selected ? Theme.text : Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13; font.bold: tab.selected }
                            StyledText { text: toolbar.bridge.categoryCounts[tab.modelData.key] || 0; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
                        }
                    }
                }
            }
        }
        TextField {
            renderType: Text.QtRendering; font.hintingPreference: Theme.textHinting
            id: inlineSearch
            objectName: "dashboardSearch"
            visible: toolbar.wide
            Layout.preferredWidth: 280; implicitHeight: 36
            implicitWidth: 280
            text: toolbar.bridge.searchQuery
            onTextEdited: toolbar.bridge.setSearch(text)
            selectByMouse: true; leftPadding: 32; rightPadding: 50
            placeholderText: toolbar.windowRef.tr("Поиск устройств")
            placeholderTextColor: Theme.muted; color: Theme.text; font.family: Theme.dataFont; font.pixelSize: 12
            Accessible.name: toolbar.windowRef.tr("Поиск устройств")
            background: CutFrame { fillColor: Theme.surface1; lineColor: inlineSearch.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall; lineWidth: inlineSearch.activeFocus ? 2 : 1 }
            Image { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: 16; height: 16; source: "../assets/brand/search.svg" }
            StyledText { visible: !inlineSearch.text.length; anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: "Ctrl K"; color: Theme.subtle; font.family: Theme.dataFont; font.pixelSize: 12 }
            CutButton { visible: !!inlineSearch.text.length; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; implicitWidth: 30; implicitHeight: 30; text: "×"; Accessible.name: toolbar.windowRef.tr("Очистить поиск"); onClicked: toolbar.bridge.setSearch("") }
        }
        CutButton {
            id: searchButton
            visible: !toolbar.wide
            implicitWidth: 36; implicitHeight: 36
            selected: !!toolbar.bridge.searchQuery
            Accessible.name: toolbar.windowRef.tr("Поиск устройств")
            ToolTip.visible: hovered; ToolTip.text: toolbar.windowRef.tr("Поиск устройств") + " · Ctrl+K"
            contentItem: Image { source: "../assets/brand/search.svg"; fillMode: Image.Pad; sourceSize: Qt.size(18,18) }
            onClicked: toolbar.focusSearch()
        }
        CutButton {
            id: refreshButton
            objectName: "dashboardRefresh"
            implicitWidth: 36; implicitHeight: 36
            enabled: !toolbar.bridge.busy
            Accessible.name: toolbar.windowRef.tr("Обновить устройства")
            ToolTip.visible: hovered; ToolTip.text: toolbar.windowRef.tr("Обновить устройства")
            contentItem: Image {
                id: refreshIcon
                source: "../assets/brand/refresh.svg"; fillMode: Image.Pad; sourceSize: Qt.size(20,20)
                RotationAnimator on rotation { from: 0; to: 360; duration: 850; loops: Animation.Infinite; running: toolbar.bridge.busy && Theme.motion > 0 }
            }
            onClicked: toolbar.bridge.refresh()
        }
        CutButton {
            id: builtinButton
            objectName: "builtinToggle"
            implicitWidth: toolbar.width < 700 ? 132 : 150; implicitHeight: 36
            background: CutFrame { fillColor: builtinButton.down ? Theme.surface3 : Theme.surface1; lineColor: builtinButton.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
            quietSelected: true
            selected: toolbar.bridge.showBuiltin
            Accessible.name: toolbar.windowRef.tr("Показывать встроенные")
            Accessible.role: Accessible.CheckBox
            Accessible.checked: toolbar.bridge.showBuiltin
            ToolTip.visible: hovered; ToolTip.text: toolbar.windowRef.tr("Показывать встроенные")
            contentItem: RowLayout {
                spacing: 6
                CutFrame { Layout.preferredWidth: 16; Layout.preferredHeight: 16; cut: 3; fillColor: Theme.background; lineColor: Theme.borderStrong
                    Rectangle { anchors.centerIn: parent; width: 6; height: 6; color: Theme.accent; visible: builtinButton.selected }
                }
                StyledText { text: toolbar.windowRef.tr("Встроенные"); font.family: Theme.displayFont; font.pixelSize: 13; color: Theme.text }
                StyledText { text: toolbar.bridge.builtinFilterCount || 0; font.family: Theme.dataFont; font.pixelSize: 12; color: Theme.subtle }
            }
            onClicked: toolbar.bridge.setShowBuiltin(!toolbar.bridge.showBuiltin)
        }
    }
    Popup {
        id: searchPopup
        objectName: "compactSearchPopup"
        x: Math.max(0, toolbar.width - width); y: toolbar.height + 4
        width: Math.min(360, toolbar.width); implicitHeight: 54
        focus: true; padding: 8
        onOpened: { compactSearch.forceActiveFocus(); compactSearch.selectAll() }
        background: CutFrame { fillColor: Theme.surface2; lineColor: Theme.borderStrong; cut: Theme.cutSmall }
        contentItem: TextField {
            renderType: Text.QtRendering; font.hintingPreference: Theme.textHinting
            id: compactSearch
            objectName: "compactDashboardSearch"
            implicitHeight: 36; implicitWidth: 280
            text: toolbar.bridge.searchQuery; onTextEdited: toolbar.bridge.setSearch(text)
            selectByMouse: true; color: Theme.text; placeholderTextColor: Theme.muted
            font.family: Theme.dataFont; font.pixelSize: 12
            placeholderText: toolbar.windowRef.tr("Поиск устройств")
            background: CutFrame { fillColor: Theme.surface1; lineColor: compactSearch.activeFocus ? Theme.accent : Theme.borderStrong; cut: Theme.cutSmall }
        }
    }
}
