import QtQuick 2.2
import "."

Rectangle
{
    id: pill
    property string text: ""
    property string tone: "neutral"
    property string iconName: ""
    property bool dot: false

    readonly property color tint:
    {
        if (tone == "success")
            return Style.success
        if (tone == "warning")
            return Style.warning
        if (tone == "danger")
            return Style.danger
        if (tone == "accent")
            return Style.accent
        return Style.textSecondary
    }

    implicitWidth: row.implicitWidth + 2 * Style.s2
    implicitHeight: Math.max(Style.px(22), label.implicitHeight + Style.s1)
    radius: height / 2
    color:
    {
        if (tone == "success")
            return Style.successSoft
        if (tone == "warning")
            return Style.warningSoft
        if (tone == "danger")
            return Style.dangerSoft
        if (tone == "accent")
            return Style.accentSoft
        return Style.surfaceAlt
    }

    Row
    {
        id: row
        anchors.centerIn: parent
        spacing: Style.s1 + Style.px(2)

        Rectangle
        {
            visible: pill.dot
            anchors.verticalCenter: parent.verticalCenter
            width: Style.px(7)
            height: width
            radius: width / 2
            color: pill.tint
        }

        Icon
        {
            visible: pill.iconName != ""
            anchors.verticalCenter: parent.verticalCenter
            name: pill.iconName
            size: Style.iconSmall
            color: pill.tint
        }

        Text
        {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            text: pill.text
            font: Style.smallStrong
            color: pill.tone == "neutral" ? Style.textSecondary : pill.tint
        }
    }
}
