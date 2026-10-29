import QtQuick
import QtQuick.Layouts
import Theme 1.0

RowLayout {
    id: led
    property bool active: false
    property string text: ""
    property color activeColor: Theme.success
    spacing: 7
    Rectangle { Layout.preferredWidth: 7; Layout.preferredHeight: 7; color: led.active ? led.activeColor : Theme.subtle }
    StyledText { text: led.text.toLocaleUpperCase(); color: led.active ? Theme.text : Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; font.letterSpacing: 0 }
}
