import QtQuick
import QtQuick.Shapes
import Theme 1.0

Shape {
    id: frame
    property color fillColor: Theme.surface1
    property color lineColor: Theme.border
    property real cut: Theme.cut
    property real lineWidth: 1
    property bool dashed: false
    readonly property real inset: lineWidth/2
    antialiasing: true
    // The software Shape renderer can ignore a ScrollView's rectangular clip.
    // Rasterize only this frame; text is a sibling and keeps direct glyph AA.
    layer.enabled: GraphicsInfo.api === GraphicsInfo.Software
    layer.smooth: true
    ShapePath {
        strokeColor: frame.lineColor
        strokeWidth: frame.lineWidth
        strokeStyle: frame.dashed ? ShapePath.DashLine : ShapePath.SolidLine
        fillColor: frame.fillColor
        startX: frame.cut; startY: frame.inset
        PathLine { x: frame.width - frame.cut; y: frame.inset }
        PathLine { x: frame.width-frame.inset; y: frame.cut }
        PathLine { x: frame.width-frame.inset; y: frame.height-frame.inset }
        PathLine { x: frame.cut; y: frame.height-frame.inset }
        PathLine { x: frame.inset; y: frame.height - frame.cut }
        PathLine { x: frame.inset; y: frame.inset }
        PathLine { x: frame.cut; y: frame.inset }
    }
}
