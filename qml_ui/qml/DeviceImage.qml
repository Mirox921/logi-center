import QtQuick

Image {
    id: image
    property url requestedSource: ""
    property bool fallbackActive: false
    signal failed(url rejectedSource)
    source: fallbackActive ? Qt.resolvedUrl("../assets/devices/fallback@2x.png") : requestedSource
    onRequestedSourceChanged: fallbackActive = false
    fillMode: Image.PreserveAspectFit
    smooth: true
    asynchronous: true
    cache: true
    sourceSize: Qt.size(Math.round(width * Screen.devicePixelRatio), Math.round(height * Screen.devicePixelRatio))
    onStatusChanged: if (status === Image.Error && !fallbackActive) {
        const rejected = source
        fallbackActive = true
        failed(rejected)
    }
}
