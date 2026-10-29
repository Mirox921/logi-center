import QtQuick
import QtQuick.Controls
import Theme 1.0

Slider {
    id: slider
    implicitHeight: 30
    background: Rectangle {
        x: slider.leftPadding; y: slider.topPadding+(slider.availableHeight-height)/2
        width: slider.availableWidth; height: 3; color: Theme.borderStrong
        Rectangle { width: slider.visualPosition*parent.width; height: parent.height; color: Theme.accent }
    }
    handle: Rectangle {
        x: slider.leftPadding+slider.visualPosition*(slider.availableWidth-width)
        y: slider.topPadding+(slider.availableHeight-height)/2
        width: 12; height: 22; color: slider.pressed ? Theme.accent : Theme.text
        border.color: slider.activeFocus ? Theme.accent : Theme.borderStrong
    }
}
