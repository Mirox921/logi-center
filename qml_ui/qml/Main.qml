import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Theme 1.0

ApplicationWindow {
    id: window
    width: 1160
    height: 800
    minimumWidth: 640
    minimumHeight: 620
    visible: true
    color: Theme.background
    title: window.bridge.simulationMode ? "Logi Center · " + window.tr("СИМУЛЯЦИЯ") : "Logi Center"
    property string page: "dashboard"
    property string previousPage: "dashboard"
    property string searchText: ""
    readonly property string categoryFilter: window.bridge.categoryFilter
    property real dashboardScrollY: 0

    function tr(value) {
        // Make QML bindings that call tr() depend on the bridge language so
        // static labels refresh immediately when the user switches language.
        const activeLanguage = bridge.language
        return bridge.tr(value)
    }
    function openDevice(deviceId) {
        bridge.selectDevice(deviceId)
        previousPage = page
        page = "device"
    }
    function openTools(target) {
        if (page === "dashboard" || page === "device") previousPage = page
        page = target
    }
    function goBack() {
        if (page !== "dashboard") {
            page = page === "device" ? "dashboard" : previousPage
            if (page === "dashboard") bridge.clearSelection()
        }
    }

    Shortcut { enabled: !window.bridge.editor.recording; sequence: "Escape"; onActivated: window.goBack() }
    Shortcut { enabled: !window.bridge.editor.recording; sequence: "Alt+Left"; onActivated: window.goBack() }
    onClosing: window.bridge.shutdown()
    Binding { target: Theme; property: "reducedMotion"; value: window.bridge.reducedMotion }
    Binding { target: window.bridge.editor; property: "observing"; value: window.visible && window.active && window.page === "device" }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppHeader { bridge: window.bridge; windowRef: window; Layout.fillWidth: true }

        StackLayout {
            id: pages
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 18; Layout.rightMargin: 18; Layout.topMargin: window.page === "dashboard" ? 0 : 12; Layout.bottomMargin: 18
            currentIndex: window.page === "dashboard" ? 0 : window.page === "device" ? 1 : window.page === "settings" ? 3 : window.page === "about" ? 4 : window.page === "backups" ? 5 : window.page === "audio" ? 6 : 2
            DashboardPage { bridge: window.bridge; windowRef: window }
            DevicePage { bridge: window.bridge; windowRef: window }
            DiagnosticsPage { bridge: window.bridge; windowRef: window }
            SettingsPage { bridge: window.bridge; windowRef: window }
            AboutPage { windowRef: window }
            BackupsPage { bridge: window.bridge; windowRef: window }
            AudioPage { bridge: window.bridge; windowRef: window }
        }
    }

    // qmllint disable unqualified
    property var bridge: deviceBridge
}
