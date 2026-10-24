import QtQuick 2.2
import "."

Item
{
    id: header
    property var txt: assistant.strings
    signal settingsClicked()
    signal projectsClicked()

    readonly property string connState: assistant.connectionState
    readonly property string tone:
    {
        if (connState == "ok")
            return "success"
        if (connState == "error")
            return "danger"
        if (connState == "not_configured")
            return "warning"
        if (connState == "checking")
            return "accent"
        return "neutral"
    }

    height: Style.px(52)

    Item
    {
        id: projectButton
        anchors.left: parent.left
        anchors.leftMargin: Style.s3
        anchors.verticalCenter: parent.verticalCenter
        width: Math.min(projectRow.implicitWidth + 2 * Style.s2, connection.x - Style.s3 - x)
        height: Style.controlLarge
        activeFocusOnTab: true
        Keys.onSpacePressed: header.projectsClicked()
        Keys.onReturnPressed: header.projectsClicked()

        Rectangle
        {
            anchors.fill: parent
            radius: Style.radius
            color: projectMouse.pressed ? Style.surfacePressed : (projectMouse.containsMouse ? Style.surfaceHover : "transparent")
            border.width: projectButton.activeFocus ? Style.focusWidth : 0
            border.color: Style.focusRing
        }

        Row
        {
            id: projectRow
            x: Style.s2
            anchors.verticalCenter: parent.verticalCenter
            spacing: Style.s1

            Text
            {
                anchors.verticalCenter: parent.verticalCenter
                text: assistant.projectName
                font: Style.title
                color: Style.text
                elide: Text.ElideRight
                width: Math.min(implicitWidth, projectButton.width - 2 * Style.s2 - Style.iconSmall - Style.s1)
            }

            Icon
            {
                anchors.verticalCenter: parent.verticalCenter
                name: "chevron-down"
                size: Style.iconSmall
            }
        }

        MouseArea
        {
            id: projectMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: header.projectsClicked()
        }

        HoverTip
        {
            area: projectMouse
            text: assistant.projectName + " · " + txt.messages_count.replace("%d", assistant.projectMessages) + "\n" + txt.projects_tip
        }
    }

    Item
    {
        id: connection
        anchors.right: settingsButton.left
        anchors.rightMargin: Style.s1
        anchors.verticalCenter: parent.verticalCenter
        width: connectionRow.implicitWidth + 2 * Style.s2
        height: Style.controlHeight
        activeFocusOnTab: true
        Keys.onSpacePressed: header.settingsClicked()
        Keys.onReturnPressed: header.settingsClicked()

        Rectangle
        {
            anchors.fill: parent
            radius: Style.radius
            color: header.tone == "danger" ? Style.dangerSoft
                 : (connectionMouse.containsMouse ? Style.surfaceHover : "transparent")
            border.width: connection.activeFocus ? Style.focusWidth : 0
            border.color: Style.focusRing
        }

        Row
        {
            id: connectionRow
            anchors.centerIn: parent
            spacing: Style.s2

            Spinner
            {
                anchors.verticalCenter: parent.verticalCenter
                visible: header.connState == "checking"
                size: Style.iconSmall
            }

            Rectangle
            {
                anchors.verticalCenter: parent.verticalCenter
                visible: header.connState != "checking"
                width: Style.px(8)
                height: width
                radius: width / 2
                color:
                {
                    if (header.tone == "success")
                        return Style.success
                    if (header.tone == "danger")
                        return Style.danger
                    if (header.tone == "warning")
                        return "#D18A1A"
                    return Style.borderStrong
                }
            }

            Text
            {
                anchors.verticalCenter: parent.verticalCenter
                text: txt["conn_short_" + header.connState] || ""
                font: header.tone == "danger" ? Style.smallStrong : Style.small
                color: header.tone == "danger" ? Style.danger : Style.textSecondary
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

        HoverTip
        {
            area: connectionMouse
            text: txt.conn_tip.replace("%s", assistant.connectionText)
                  + (assistant.connectionDetail != "" ? "\n" + assistant.connectionDetail : "")
        }
    }

    IconButton
    {
        id: settingsButton
        anchors.right: parent.right
        anchors.rightMargin: Style.s3
        anchors.verticalCenter: parent.verticalCenter
        iconName: "settings"
        tooltip: txt.settings
        onClicked: header.settingsClicked()
    }
}
