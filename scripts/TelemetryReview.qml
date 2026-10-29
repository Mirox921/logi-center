import QtQuick
import QtQuick.Layouts
import "../qml_ui/qml"
import Theme 1.0
Window {
    width: 920; height: 580; visible: true; color: Theme.background
    Column {
        x: 20; y: 20; spacing: 22
        Flow {
            width: 880; spacing: 12
            Repeater {
                model: ["USB","2.4G","BT","I²C","Linux Input","libratbag","Solaar","Беспроводное"]
                delegate: ConnectionTag { required property string modelData; objectName: "tag-"+modelData; label: modelData }
            }
        }
        Repeater {
            model: [0,1,25,46,50,99,100]
            delegate: SegmentedBattery { required property int modelData; objectName:"meter-"+modelData; width: 400; percent:modelData; label:modelData+"%" }
        }
    }
}
