import QtQuick

CutInput {
    id: input
    property var numberValue: null
    signal numberCommitted(var value)
    function syncValue() {
        if (!activeFocus) text=numberValue===null || numberValue===undefined ? "" : String(numberValue)
    }
    Component.onCompleted: syncValue()
    onNumberValueChanged: syncValue()
    onEditingFinished: {
        numberCommitted(Number(text))
        Qt.callLater(syncValue)
    }
}
