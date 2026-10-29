pragma ComponentBehavior: Bound
import QtQuick
import Theme 1.0

Item {
    id: section
    required property var deviceModel
    required property var windowRef
    property string indexText: "01"
    property string title: ""
    property int columns: width >= 1480 ? 4 : width >= 1080 ? 3 : width >= 700 ? 2 : 1
    readonly property int cellHeight: 416
    visible: deviceModel.count > 0
    readonly property int rowCount: Math.ceil(deviceModel.count / columns)
    implicitHeight: visible ? flow.y + flow.height + 6 : 0
    height: implicitHeight

    SectionHeader {
        id: header
        width: section.width
        height: 20
        indexText: section.indexText
        title: section.windowRef.tr(section.title)
        countText: section.deviceModel.count.toString().padStart(2, "0")
    }
    Flow {
        id: flow
        y: header.height + 8
        width: section.width
        height: section.rowCount > 0 ? section.rowCount * section.cellHeight - 10 : 0
        spacing: 10
        Repeater {
            model: section.deviceModel
            delegate: DeviceCard {
                required property var device
                width: (flow.width - (section.columns - 1) * flow.spacing) / section.columns
                height: section.cellHeight - 10
                deviceData: device
                windowRef: section.windowRef
                onOpen: function(deviceId) { section.windowRef.openDevice(deviceId) }
            }
        }
    }
}
