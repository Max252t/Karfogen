import QtQuick 2.2
import UM 1.2 as UM
import "."

Rectangle
{
    id: header
    property var txt: assistant.strings
    signal settingsClicked()

    width: parent ? parent.width : implicitWidth
    height: Math.max(titleColumn.height, Style.controlHeight) + 2 * Style.narrow
    color: Style.background

    Column
    {
        id: titleColumn
        anchors.left: parent.left
        anchors.leftMargin: Style.margin
        anchors.right: connection.left
        anchors.rightMargin: Style.margin
        anchors.verticalCenter: parent.verticalCenter

        Text
        {
            width: parent.width
            text: assistant.projectName
            font: Style.fontHeading
            color: Style.text
            elide: Text.ElideRight
        }

        Text
        {
            width: parent.width
            text: txt.messages_count.replace("%d", assistant.projectMessages)
            font: Style.fontSmall
            color: Style.textSecondary
            elide: Text.ElideRight
        }
    }

    Rectangle
    {
        id: connection
        anchors.right: settingsButton.left
        anchors.rightMargin: Style.narrow
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(dot.width + connectionText.implicitWidth + 3 * Style.narrow, header.width * 0.45)
        height: Math.round(Style.controlHeight * 0.8)
        radius: height / 2
        color: connectionMouse.containsMouse ? Style.panel : "transparent"
        border.width: Style.lineWidth
        border.color: Style.hairline

        Row
        {
            id: connectionRow
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: parent.left
            anchors.leftMargin: Style.narrow
            spacing: Style.narrow

            Rectangle
            {
                id: dot
                anchors.verticalCenter: parent.verticalCenter
                width: Math.round(8 * Style.scale)
                height: width
                radius: width / 2
                color:
                {
                    var state = assistant.connectionState
                    if (state == "ok")
                        return Style.success
                    if (state == "error")
                        return Style.danger
                    if (state == "not_configured")
                        return Style.warning
                    if (state == "checking")
                        return Style.primary
                    return Style.textMuted
                }
            }

            Text
            {
                id: connectionText
                anchors.verticalCenter: parent.verticalCenter
                width: connection.width - 3 * Style.narrow - dot.width
                text: assistant.connectionText
                font: Style.fontSmall
                color: Style.textSecondary
                elide: Text.ElideRight
            }
        }

        MouseArea
        {
            id: connectionMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: header.settingsClicked()
        }

        UM.TooltipArea
        {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            text: assistant.connectionDetail
        }
    }

    IconButton
    {
        id: settingsButton
        anchors.right: parent.right
        anchors.rightMargin: Style.narrow
        anchors.verticalCenter: parent.verticalCenter
        iconName: "settings"
        tooltip: txt.settings
        onClicked: header.settingsClicked()
    }

    Rectangle
    {
        anchors.bottom: parent.bottom
        width: parent.width
        height: Style.lineWidth
        color: Style.hairline
    }
}
