import QtQuick 2.2
import "."

Item
{
    id: section
    property string text: ""
    property string badge: ""
    width: parent ? parent.width : implicitWidth
    implicitHeight: title.implicitHeight + Style.narrow
    height: implicitHeight

    Text
    {
        id: title
        anchors.left: parent.left
        anchors.right: badgeBox.visible ? badgeBox.left : parent.right
        anchors.rightMargin: Style.narrow
        anchors.verticalCenter: parent.verticalCenter
        text: section.text
        font: Style.fontHeading
        color: Style.text
        elide: Text.ElideRight
    }

    Rectangle
    {
        id: badgeBox
        visible: section.badge != "" && section.badge != "0"
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(height, badgeText.implicitWidth + Style.margin)
        height: badgeText.implicitHeight + Style.narrow
        radius: height / 2
        color: Style.primaryTint

        Text
        {
            id: badgeText
            anchors.centerIn: parent
            text: section.badge
            font: Style.fontSmall
            color: Style.primary
        }
    }
}
