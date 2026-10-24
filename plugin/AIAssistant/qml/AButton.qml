import QtQuick 2.2
import "."

Item
{
    id: control

    property string text: ""
    property string iconName: ""
    property string variant: "secondary"
    property string size: "normal"
    property string tooltip: ""
    property bool iconOnly: false
    signal clicked()

    readonly property bool hovered: mouse.containsMouse
    readonly property bool down: mouse.pressed
    readonly property int pad: size == "small" ? Style.s2 : Style.s3
    readonly property bool showLabel: text != "" && !iconOnly
    readonly property color foreground:
    {
        if (!enabled)
            return Style.textMuted
        if (variant == "primary")
            return Style.textOnAccent
        if (variant == "danger")
            return Style.danger
        if (variant == "link")
            return hovered ? Style.accentHover : Style.accent
        return Style.text
    }

    implicitHeight: size == "small" ? Style.controlSmall : (size == "large" ? Style.controlLarge : Style.controlHeight)
    implicitWidth: iconOnly ? implicitHeight
                   : (iconName != "" ? Style.iconSize + (showLabel ? Style.s2 : 0) : 0) + label.implicitWidth + 2 * pad
    activeFocusOnTab: enabled
    Keys.onSpacePressed: control.clicked()
    Keys.onReturnPressed: control.clicked()
    Keys.onEnterPressed: control.clicked()

    Rectangle
    {
        id: focusRing
        anchors.fill: parent
        anchors.margins: -Style.focusWidth
        radius: background.radius + Style.focusWidth
        color: "transparent"
        border.width: Style.focusWidth
        border.color: Style.focusRing
        visible: control.activeFocus
    }

    Rectangle
    {
        id: background
        anchors.fill: parent
        radius: control.variant == "link" ? Style.radiusSmall : Style.radius
        color:
        {
            var v = control.variant
            if (v == "primary")
                return !control.enabled ? Style.surfaceAlt : (control.down ? Style.accentPressed : (control.hovered ? Style.accentHover : Style.accent))
            if (v == "danger")
                return control.down ? Style.dangerSoftHover : (control.hovered ? Style.dangerSoftHover : Style.dangerSoft)
            if (v == "secondary")
                return !control.enabled ? Style.surfaceAlt : (control.down ? Style.surfacePressed : (control.hovered ? Style.surfaceHover : Style.surfaceAlt))
            if (v == "accent")
                return control.down ? Style.accentSoftHover : (control.hovered ? Style.accentSoftHover : Style.accentSoft)
            if (v == "ghost")
                return control.down ? Style.surfacePressed : (control.hovered ? Style.surfaceHover : "transparent")
            return "transparent"
        }
        Behavior on color { ColorAnimation { duration: Style.hoverMs } }
    }

    Row
    {
        anchors.centerIn: parent
        spacing: Style.s2

        Icon
        {
            id: icon
            anchors.verticalCenter: parent.verticalCenter
            visible: control.iconName != ""
            name: control.iconName
            color: control.variant == "accent" ? Style.accent : control.foreground
        }

        Text
        {
            id: label
            anchors.verticalCenter: parent.verticalCenter
            visible: control.showLabel
            text: control.text
            font: control.variant == "primary" || control.variant == "accent" ? Style.bodyStrong : Style.body
            color: control.variant == "accent" ? Style.accent : control.foreground
            elide: Text.ElideRight
            width: Math.max(0, Math.min(implicitWidth, control.width - 2 * control.pad
                                        - (icon.visible ? Style.iconSize + Style.s2 : 0)))
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

    HoverTip
    {
        area: mouse
        text: control.tooltip != "" ? control.tooltip : (control.iconOnly ? control.text : "")
    }
}
