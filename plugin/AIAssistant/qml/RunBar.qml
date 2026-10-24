import QtQuick 2.2
import "."

Item
{
    id: bar
    property var txt: assistant.strings
    property bool showStop: true

    visible: assistant.running
    height: visible ? Style.controlLarge + Style.s2 : 0

    Rectangle
    {
        x: Style.s3
        width: parent.width - 2 * Style.s3
        height: Style.controlLarge
        radius: Style.radius
        color: Style.accentSoft
        clip: true

        Spinner
        {
            id: spinner
            anchors.left: parent.left
            anchors.leftMargin: Style.s3
            anchors.verticalCenter: parent.verticalCenter
            running: bar.visible
        }

        Text
        {
            anchors.left: spinner.right
            anchors.leftMargin: Style.s2
            anchors.right: bar.showStop ? stopButton.left : parent.right
            anchors.rightMargin: Style.s2
            anchors.verticalCenter: parent.verticalCenter
            text: assistant.statusText
            font: Style.bodyStrong
            color: Style.accent
            elide: Text.ElideRight
        }

        Rectangle
        {
            visible: assistant.sliceState == "slicing"
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            height: Style.px(2)
            width: parent.width * assistant.sliceProgress
            color: Style.accent
        }

        AButton
        {
            id: stopButton
            visible: bar.showStop
            anchors.right: parent.right
            anchors.rightMargin: Style.px(4)
            anchors.verticalCenter: parent.verticalCenter
            size: "small"
            variant: "ghost"
            iconName: "stop"
            text: assistant.stopping ? txt.run_stopping : txt.stop
            enabled: !assistant.stopping
            onClicked: assistant.stopAgent()
        }
    }
}
