import QtQuick 2.2
import "."

Rectangle
{
    id: bar
    property var txt: assistant.strings

    width: parent ? parent.width : implicitWidth
    height: visible ? Style.controlHeight + Style.narrow : 0
    color: Style.primaryTint
    visible: assistant.running

    Spinner
    {
        id: spinner
        anchors.left: parent.left
        anchors.leftMargin: Style.margin
        anchors.verticalCenter: parent.verticalCenter
        running: bar.visible
    }

    Text
    {
        anchors.left: spinner.right
        anchors.leftMargin: Style.narrow
        anchors.right: stopButton.left
        anchors.rightMargin: Style.narrow
        anchors.verticalCenter: parent.verticalCenter
        text: assistant.statusText
        font: Style.font
        color: Style.primary
        elide: Text.ElideRight
    }

    Rectangle
    {
        visible: assistant.sliceState == "slicing"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        height: Math.round(2 * Style.scale)
        width: parent.width * assistant.sliceProgress
        color: Style.primary
    }

    AButton
    {
        id: stopButton
        anchors.right: parent.right
        anchors.rightMargin: Style.margin
        anchors.verticalCenter: parent.verticalCenter
        compact: true
        variant: "danger"
        iconName: "cross1"
        text: assistant.stopping ? txt.run_stopping : txt.stop
        enabled: !assistant.stopping
        onClicked: assistant.stopAgent()
    }
}
