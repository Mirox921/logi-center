pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Theme 1.0

RowLayout {
    id: battery
    property real percent: -1
    property bool charging: false
    property string label: ""
    property int runningSegment: 0
    readonly property int filledSegments: percent >= 0 ? Math.floor(percent/100*12) : 0
    spacing: 12
    Row {
        spacing: 2
        Repeater {
            model: 12
            delegate: Rectangle {
                required property int index
                width: 7; height: 12
                color: battery.percent >= 0 && index < battery.filledSegments ? Theme.accent : battery.percent >= 0 ? Theme.surface3 : "transparent"
                border.width: battery.percent >= 0 ? 1 : 0
                border.color: battery.charging && index === battery.runningSegment ? Theme.charging : Theme.borderStrong
                opacity: battery.percent >= 0 || battery.charging ? .95 : .65
                Repeater {
                    model: battery.percent < 0 ? 2 : 0
                    delegate: Rectangle {
                        required property int index
                        width: 2; height: 2; y: 5; x: index === 0 ? 1 : 4
                        color: Theme.subtle
                    }
                }
            }
        }
        Rectangle { width: 3; height: 5; y: 3; color: battery.percent >= 100 ? Theme.accent : Theme.borderStrong }
    }
    StyledText {
        Layout.fillWidth: true
        text: battery.label
        color: battery.percent < 0 ? Theme.subtle : Theme.text
        font.family: Theme.dataFont
        font.pixelSize: battery.percent < 0 ? 12 : 18
        horizontalAlignment: Text.AlignRight
        elide: Text.ElideRight
    }
    Timer { interval: 400; repeat: true; running: battery.charging && Theme.motion > 0; onTriggered: battery.runningSegment = (battery.runningSegment + 1) % 12 }
}
