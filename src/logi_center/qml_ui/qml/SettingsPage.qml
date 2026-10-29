import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ScrollView {
    id: settings
    required property var bridge
    required property var windowRef
    ColumnLayout {
        width: settings.availableWidth
        spacing: 18
        SectionHeader { title: settings.windowRef.tr("Настройки"); indexText: "01"; countText: ""; Layout.fillWidth: true }
        StyledText { text: settings.windowRef.tr("Язык интерфейса"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18 }
        RowLayout {
            CutButton { text: "Русский"; selected: settings.bridge.language === "ru"; onClicked: settings.bridge.setLanguage("ru") }
            CutButton { text: "English"; selected: settings.bridge.language === "en"; onClicked: settings.bridge.setLanguage("en") }
        }
        StyledText { text: settings.windowRef.tr("Масштаб интерфейса"); color: Theme.text; font.family: Theme.displayFont; font.pixelSize: 18 }
        CutCombo {
            objectName: "ui-scale-selector"
            readonly property var percentages: [75,90,100,110,125,150,175,200]
            model: percentages.map(value => value+"%")
            currentIndex: percentages.indexOf(settings.bridge.uiScale)
            onActivated: index => settings.bridge.setUiScale(percentages[index])
            Layout.preferredWidth: 240
        }
        StyledText {
            text: settings.windowRef.tr(settings.bridge.scaleRestartRequired ? "Масштаб изменится после перезапуска Logi Center." : "Масштаб приложения дополняет масштаб системы; GTK не изменяется.")
            color: settings.bridge.scaleRestartRequired ? Theme.warning : Theme.muted
            font.family: Theme.displayFont; font.pixelSize: 13; wrapMode: Text.Wrap; Layout.fillWidth: true
        }
        CutButton {
            text: (settings.bridge.showBuiltin ? "✓ " : "□ ") + settings.windowRef.tr("Показывать встроенные")
            selected: settings.bridge.showBuiltin
            onClicked: settings.bridge.setShowBuiltin(!settings.bridge.showBuiltin)
        }
        CutButton { text: (settings.bridge.reducedMotion ? "✓ " : "□ ") + settings.windowRef.tr("Уменьшить анимацию"); selected: settings.bridge.reducedMotion; enabled: !settings.bridge.systemReducedMotion; onClicked: settings.bridge.setReducedMotion(!settings.bridge.reducedMotion) }
        StyledText { visible: settings.bridge.systemReducedMotion; text: settings.windowRef.tr("Анимация отключена системой"); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12 }
        StyledText { visible: !!settings.bridge.preferencesError; text: settings.bridge.preferencesError; color: Theme.error; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        StyledText { text: settings.windowRef.tr(settings.bridge.persistUi ? "Параметры сохраняются локально. Аппаратные настройки не изменяются." : "Настройки этой сессии. Аппаратные параметры не изменяются."); color: Theme.muted; font.family: Theme.dataFont; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
    }
}
