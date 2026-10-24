import QtQuick 2.2
import UM 1.2 as UM
import "."

Rectangle
{
    id: control

    property string text: ""
    property string iconName: ""
    property string variant: "secondary"
    property string tooltip: ""
    property bool compact: false
    signal clicked()

    readonly property bool hovered: mouse.containsMouse
    readonly property int sidePadding: compact ? Style.narrow : Style.margin
    readonly property color foreground:
    {
        if (variant == "primary")
            return Style.primaryText
        if (variant == "danger")
            return Style.danger
        if (variant == "link" || variant == "ghost")
            return hovered ? Style.primaryHover : Style.primary
        return Style.text
    }

    implicitHeight: compact ? Math.round(Style.controlHeight * 0.8) : Style.controlHeight
    implicitWidth: (iconName != "" ? Style.smallIcon : 0) + (iconName != "" && text != "" ? Style.narrow : 0)
                   + label.implicitWidth + 2 * sidePadding
    radius: Style.radius
    opacity: enabled ? 1.0 : 0.45
    activeFocusOnTab: enabled
    color:
    {
        if (variant == "primary")
            return hovered ? Style.primaryHover : Style.primary
        if (variant == "danger")
            return hovered ? Style.dangerTint : Style.background
        if (variant == "ghost")
            return hovered ? Style.primaryTint : "transparent"
        if (variant == "link")
            return "transparent"
        return hovered ? Style.panel : Style.background
    }
    border.width: (variant == "secondary" || variant == "danger" || activeFocus) ? Style.lineWidth : 0
    border.color: activeFocus ? Style.fieldFocus : (variant == "danger" ? Style.danger : Style.lining)

    Keys.onSpacePressed: control.clicked()
    Keys.onReturnPressed: control.clicked()

    Row
    {
        id: content
        anchors.centerIn: parent
        spacing: Style.narrow

        UM.RecolorImage
        {
            id: icon
            visible: control.iconName != ""
            anchors.verticalCenter: parent.verticalCenter
            width: Style.smallIcon
            height: Style.smallIcon
            sourceSize.width: width
            sourceSize.height: height
            source: control.iconName != "" ? UM.Theme.getIcon(control.iconName) : ""
            color: control.foreground
        }

        Text
        {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            text: control.text
            visible: text != ""
            font: control.variant == "primary" ? Style.fontBold : Style.font
            color: control.foreground
            elide: Text.ElideRight
            width: Math.max(0, Math.min(implicitWidth, control.width - 2 * control.sidePadding
                                        - (icon.visible ? Style.smallIcon + content.spacing : 0)))
        }
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
        visible: control.tooltip != ""
    }
}
