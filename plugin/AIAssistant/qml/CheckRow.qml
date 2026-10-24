import QtQuick 2.2
import UM 1.2 as UM
import "."

Item
{
    id: row
    property bool checked: false
    property string text: ""
    property string secondary: ""
    signal toggled(bool checked)

    width: parent ? parent.width : implicitWidth
    height: Math.max(box.height, labels.height)
    activeFocusOnTab: enabled
    opacity: enabled ? 1.0 : 0.5

    function toggle()
    {
        row.checked = !row.checked
        row.toggled(row.checked)
    }

    Keys.onSpacePressed: row.toggle()

    Rectangle
    {
        id: box
        width: Math.round(Style.controlHeight * 0.7)
        height: width
        radius: Style.radius
        color: row.checked ? Style.primary : Style.field
        border.width: Style.lineWidth
        border.color: row.activeFocus || mouse.containsMouse ? Style.fieldFocus : (row.checked ? Style.primary : Style.fieldBorder)

        UM.RecolorImage
        {
            anchors.centerIn: parent
            width: Math.round(parent.width * 0.6)
            height: width
            sourceSize.width: width
            sourceSize.height: height
            visible: row.checked
            source: UM.Theme.getIcon("check-outline")
            color: Style.primaryText
        }
    }

    Column
    {
        id: labels
        anchors.left: box.right
        anchors.leftMargin: Style.narrow
        anchors.right: parent.right

        Text
        {
            width: parent.width
            text: row.text
            font: Style.font
            color: Style.text
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Text
        {
            width: parent.width
            visible: row.secondary != ""
            text: row.secondary
            font: Style.fontSmall
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
