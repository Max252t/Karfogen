import QtQuick 2.2
import "."

Item
{
    id: bar
    property string current: "chat"
    property var items: []
    signal selected(string name)

    height: Style.controlHeight + Style.s2

    Row
    {
        x: Style.s3
        anchors.top: parent.top
        spacing: Style.s1

        Repeater
        {
            model: bar.items

            Item
            {
                id: tab
                property bool active: bar.current == modelData.name
                width: tabRow.implicitWidth + 2 * Style.s3
                height: Style.controlHeight
                activeFocusOnTab: true
                Keys.onSpacePressed: bar.selected(modelData.name)
                Keys.onReturnPressed: bar.selected(modelData.name)

                Rectangle
                {
                    anchors.fill: parent
                    radius: Style.radius
                    color: tab.active ? Style.accentSoft : (tabMouse.containsMouse ? Style.surfaceHover : "transparent")
                    border.width: tab.activeFocus ? Style.focusWidth : 0
                    border.color: Style.focusRing
                    Behavior on color { ColorAnimation { duration: Style.hoverMs } }
                }

                Row
                {
                    id: tabRow
                    anchors.centerIn: parent
                    spacing: Style.s1 + Style.px(2)

                    Text
                    {
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        font: tab.active ? Style.bodyStrong : Style.body
                        color: tab.active ? Style.accent : (tabMouse.containsMouse ? Style.text : Style.textSecondary)
                    }

                    Text
                    {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: modelData.badge > 0
                        text: modelData.badge
                        font: Style.small
                        color: tab.active ? Style.accent : Style.textMuted
                    }
                }

                MouseArea
                {
                    id: tabMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bar.selected(modelData.name)
                }
            }
        }
    }
}
