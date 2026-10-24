import QtQuick 2.2
import "."

Rectangle
{
    id: toast
    property string kind: "info"

    function show(message, kind)
    {
        label.text = message
        toast.kind = kind || "info"
        toast.opacity = 1
        hideTimer.interval = toast.kind == "error" ? 9000 : 6000
        hideTimer.restart()
    }

    anchors.horizontalCenter: parent.horizontalCenter
    width: Math.min(row.implicitWidth + 2 * Style.s3, parent.width - 2 * Style.s4)
    height: Math.max(Style.controlHeight, label.height + 2 * Style.s2)
    radius: Style.radius
    color: Style.toast
    opacity: 0
    visible: opacity > 0
    z: 100

    Behavior on opacity { NumberAnimation { duration: 150 } }

    Row
    {
        id: row
        x: Style.s3
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.s2

        Icon
        {
            anchors.verticalCenter: parent.verticalCenter
            name: toast.kind == "success" ? "check-circle" : (toast.kind == "error" ? "alert" : (toast.kind == "warning" ? "warning" : "info"))
            color: toast.kind == "success" ? "#7BD69A" : (toast.kind == "error" ? "#FF9A92" : (toast.kind == "warning" ? "#F5C46B" : "#B9C2CC"))
        }

        Text
        {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(implicitWidth, toast.parent.width - 4 * Style.s4 - Style.iconSize)
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            font: Style.body
            color: Style.toastText
        }
    }

    MouseArea
    {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        onClicked: toast.opacity = 0
    }

    Timer
    {
        id: hideTimer
        interval: 6000
        running: false
        onTriggered:
        {
            if (hover.containsMouse)
                restart()
            else
                toast.opacity = 0
        }
    }
}
