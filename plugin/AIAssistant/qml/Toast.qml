import QtQuick 2.2
import "."

Rectangle
{
    id: toast

    function show(message)
    {
        label.text = message
        toast.opacity = 1
        hideTimer.restart()
    }

    anchors.horizontalCenter: parent.horizontalCenter
    anchors.bottom: parent.bottom
    anchors.bottomMargin: Style.wide * 4
    width: Math.min(label.implicitWidth, parent.width - 4 * Style.wide) + 2 * Style.margin
    height: label.height + 2 * Style.narrow
    radius: Style.radius
    color: Style.toastBackground
    opacity: 0
    visible: opacity > 0
    z: 100

    Behavior on opacity { NumberAnimation { duration: 180 } }

    Text
    {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, toast.parent.width - 4 * Style.wide)
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        font: Style.font
        color: Style.toastText
        horizontalAlignment: Text.AlignHCenter
    }

    MouseArea
    {
        anchors.fill: parent
        onClicked: toast.opacity = 0
    }

    Timer
    {
        id: hideTimer
        interval: 4500
        onTriggered: toast.opacity = 0
    }
}
