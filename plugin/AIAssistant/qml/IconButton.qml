import QtQuick 2.2
import UM 1.2 as UM
import "."

Rectangle
{
    id: control

    property string iconName: "settings"
    property string tooltip: ""
    property bool danger: false
    property color iconColor: danger ? Style.danger : (mouse.containsMouse ? Style.primary : Style.textSecondary)
    signal clicked()

    implicitWidth: Style.controlHeight
    implicitHeight: Style.controlHeight
    radius: Style.radius
    color: mouse.containsMouse ? (danger ? Style.dangerTint : Style.primaryTint) : "transparent"
    border.width: activeFocus ? Style.lineWidth : 0
    border.color: Style.fieldFocus
    opacity: enabled ? 1.0 : 0.4
    activeFocusOnTab: enabled
    Keys.onSpacePressed: control.clicked()
    Keys.onReturnPressed: control.clicked()

    UM.RecolorImage
    {
        anchors.centerIn: parent
        width: Style.icon
        height: Style.icon
        sourceSize.width: width
        sourceSize.height: height
        source: UM.Theme.getIcon(control.iconName)
        color: control.iconColor
    }

    MouseArea
    {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: control.clicked()
    }

    UM.TooltipArea
    {
        anchors.fill: parent
        text: control.tooltip
        acceptedButtons: Qt.NoButton
    }
}
