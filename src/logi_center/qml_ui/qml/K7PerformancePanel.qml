pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import Theme 1.0

ColumnLayout {
    id: root
    required property var controller
    required property var windowRef
    readonly property var fields: controller.k7Fields
    spacing: 12
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Параметры прочитаны с K7. Черновик не меняет мышь; результат записи проверяется чтением. Новые команды требуют физической проверки.")
        color: Theme.muted; font.family: Theme.displayFont; font.pixelSize: 13
    }
    GridLayout {
        Layout.fillWidth: true
        columns: width>=850 ? 2 : 1
        columnSpacing: 12; rowSpacing: 12
        Repeater {
            model: ["mchose:sensor_config:performance_mode","mchose:sensor_config:rotation",
                    "mchose:sleep","mchose:sensor_config:ripple",
                    "mchose:sensor_config:lod","mchose:sensor_config:angle_snap",
                    "mchose:debounce","mchose:sensor_config:motion_sync"]
            delegate: Loader {
                id: cell
                required property string modelData
                Layout.fillWidth: true; Layout.preferredWidth: 380; Layout.alignment: Qt.AlignTop
                Layout.preferredHeight: item ? item.implicitHeight : 0
                active: !!root.fields[modelData]
                sourceComponent: ControlEditor {
                    field: root.fields[cell.modelData]
                    controller: root.controller; windowRef: root.windowRef
                }
            }
        }
    }
    StyledText {
        Layout.fillWidth: true; wrapMode: Text.Wrap
        text: root.windowRef.tr("Режим сенсора и фильтры могут влиять на отклик и расход батареи. Неподдерживаемые значения не отправляются; другие настройки сохраняются.")
        color: Theme.subtle; font.family: Theme.displayFont; font.pixelSize: 13
    }
}
