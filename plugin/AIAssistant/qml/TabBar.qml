import QtQuick 2.2
import "."

Rectangle
{
    id: tabs
    property string current: "chat"
    property var items: []
    signal selected(string name)

    width: parent ? parent.width : implicitWidth
    height: Style.controlHeight + Style.narrow
    color: Style.background

    Row
    {
        anchors.left: parent.left
        anchors.leftMargin: Style.margin
        anchors.bottom: parent.bottom
        spacing: Style.wide

        Repeater
        {
            model: tabs.items

            Item
            {
                id: tab
                property bool active: tabs.current == modelData.name
                width: tabRow.width
                height: tabs.height

                Row
                {
                    id: tabRow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Style.narrow

                    Text
                    {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        font: tab.active ? Style.fontBold : Style.font
                        color: tab.active ? Style.primary : (tabMouse.containsMouse ? Style.text : Style.textSecondary)
                    }

                    Rectangle
                    {
                        visible: modelData.badge > 0
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.max(height, badgeText.implicitWidth + Style.narrow * 2)
                        height: badgeText.implicitHeight + Math.round(Style.narrow / 2)
                        radius: height / 2
                        color: Style.primaryTint

                        Text
                        {
                            id: badgeText
                            anchors.centerIn: parent
                            text: modelData.badge
                            font: Style.fontSmall
                            color: Style.primary
                        }
                    }
                }

                Rectangle
                {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: Math.round(2 * Style.scale)
                    color: Style.primary
                    visible: tab.active
                }

                MouseArea
                {
                    id: tabMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: tabs.selected(modelData.name)
                }
            }
        }
    }

    Rectangle
    {
        anchors.bottom: parent.bottom
        width: parent.width
        height: Style.lineWidth
        color: Style.hairline
    }
}
