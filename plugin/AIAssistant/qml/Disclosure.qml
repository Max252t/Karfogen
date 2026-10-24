import QtQuick 2.2
import "."

Item
{
    id: disclosure
    property string text: ""
    property string badge: ""
    property bool open: false
    default property alias content: body.children

    width: parent ? parent.width : implicitWidth
    height: header.height + (open ? body.height + Style.s2 : 0)
    clip: true

    Item
    {
        id: header
        width: parent.width
        height: Style.controlHeight
        activeFocusOnTab: true
        Keys.onSpacePressed: disclosure.open = !disclosure.open
        Keys.onReturnPressed: disclosure.open = !disclosure.open

        Rectangle
        {
            anchors.fill: parent
            anchors.leftMargin: -Style.s2
            anchors.rightMargin: -Style.s2
            radius: Style.radius
            color: headerMouse.containsMouse ? Style.surfaceAlt : "transparent"
            border.width: header.activeFocus ? Style.focusWidth : 0
            border.color: Style.focusRing
        }

        Icon
        {
            id: chevron
            anchors.verticalCenter: parent.verticalCenter
            name: disclosure.open ? "chevron-down" : "chevron-right"
            size: Style.iconSmall
        }

        Text
        {
            anchors.left: chevron.right
            anchors.leftMargin: Style.s2
            anchors.right: count.left
            anchors.rightMargin: Style.s2
            anchors.verticalCenter: parent.verticalCenter
            text: disclosure.text
            font: Style.bodyStrong
            color: Style.text
            elide: Text.ElideRight
        }

        Text
        {
            id: count
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            visible: disclosure.badge != "" && disclosure.badge != "0"
            text: disclosure.badge
            font: Style.small
            color: Style.textMuted
        }

        MouseArea
        {
            id: headerMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: disclosure.open = !disclosure.open
        }
    }

    Column
    {
        id: body
        anchors.top: header.bottom
        anchors.topMargin: Style.s2
        width: parent.width
        spacing: Style.s3
        visible: disclosure.open
    }
}
