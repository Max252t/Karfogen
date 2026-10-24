import QtQuick 2.2
import "."

Item
{
    id: row
    property bool checked: false
    property string text: ""
    property string secondary: ""
    signal toggled(bool checked)

    width: parent ? parent.width : implicitWidth
    height: Math.max(Style.controlSmall, labels.height)
    activeFocusOnTab: enabled

    function toggle()
    {
        row.checked = !row.checked
        row.toggled(row.checked)
    }

    Keys.onSpacePressed: row.toggle()

    Rectangle
    {
        id: box
        y: Math.max(0, (Math.min(row.height, Style.controlSmall) - height) / 2)
        width: Style.px(18)
        height: width
        radius: Style.px(5)
        color: row.checked ? Style.accent : Style.surface
        border.width: row.checked ? 0 : Style.line + (mouse.containsMouse ? 0 : 0)
        border.color: mouse.containsMouse ? Style.accent : Style.borderStrong
        Behavior on color { ColorAnimation { duration: Style.hoverMs } }

        Rectangle
        {
            anchors.fill: parent
            anchors.margins: -Style.focusWidth - Style.px(1)
            radius: parent.radius + Style.focusWidth
            color: "transparent"
            border.width: Style.focusWidth
            border.color: Style.focusRing
            visible: row.activeFocus
        }

        Icon
        {
            anchors.centerIn: parent
            visible: row.checked
            name: "check"
            size: Style.iconSmall
            color: Style.textOnAccent
        }
    }

    Column
    {
        id: labels
        anchors.left: box.right
        anchors.leftMargin: Style.s2 + Style.px(2)
        anchors.right: parent.right
        y: Math.max(0, (Style.controlSmall - first.height) / 2)
        spacing: Style.px(2)

        Text
        {
            id: first
            width: parent.width
            text: row.text
            font: Style.body
            color: row.enabled ? Style.text : Style.textMuted
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Text
        {
            width: parent.width
            visible: row.secondary != ""
            text: row.secondary
            font: Style.small
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }
    }

    MouseArea
    {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: row.toggle()
    }
}
