pragma Singleton
import QtQuick

QtObject {
    readonly property string assetRoot: typeof logiAssetsUrl !== "undefined" ? logiAssetsUrl : ""
    readonly property color background: "#171713"
    readonly property color surface1: "#211f1a"
    readonly property color surface2: "#292720"
    readonly property color surface3: "#343129"
    readonly property color surface4: "#3e3a31"
    readonly property color border: "#514c41"
    readonly property color borderStrong: "#756d5d"
    readonly property color accent: "#f3aa32"
    readonly property color accentSoft: "#4b3519"
    readonly property color text: "#f4f0e7"
    readonly property color muted: "#c3bcad"
    readonly property color subtle: "#a39b8c"
    readonly property color success: "#8bc58a"
    readonly property color warning: "#f3c866"
    readonly property color error: "#f08072"
    readonly property color charging: "#f3aa32"
    readonly property int cut: 11
    readonly property int cutSmall: 6
    readonly property int gapXs: 5
    readonly property int gapSm: 9
    readonly property int gapMd: 14
    readonly property int gapLg: 21
    readonly property int gapXl: 30
    readonly property int textHinting: Font.PreferNoHinting
    property bool reducedMotion: false
    readonly property int motion: reducedMotion ? 0 : 170
    readonly property string displayFont: "Noto Sans"
    readonly property string dataFont: "JetBrainsMono Nerd Font"
}
