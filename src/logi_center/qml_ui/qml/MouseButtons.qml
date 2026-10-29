pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    G502ButtonPanel { visible: root.controller.g502Editor; controller: root.controller; windowRef: root.windowRef; Layout.fillWidth: true }
    Loader {
        Layout.fillWidth: true; Layout.preferredHeight: item ? item.implicitHeight : 0
        active: !root.controller.g502Editor
        sourceComponent: GenericMouseButtons { controller: root.controller; windowRef: root.windowRef }
    }
}
