import QtQuick 2.2
import "."

Item
{
    id: control

    property string iconName: "settings"
    property string tooltip: ""
    property string tone: "normal"
    property bool checked: false
    signal clicked()

    readonly property bool hovered: mouse.containsMouse

    implicitWidth: Style.controlHeight
    implicitHeight: Style.controlHeight
    activeFocusOnTab: enabled
    Keys.onSpacePressed: control.clicked()
    Keys.onReturnPressed: control.clicked()
    Keys.onEnterPressed: control.clicked()

    Rectangle
    {
        anchors.fill: parent
        anchors.margins: -Style.focusWidth
        radius: Style.radius + Style.focusWidth
        color: "transparent"
        border.width: Style.focusWidth
        border.color: Style.focusRing
        visible: control.activeFocus
    }

    Rectangle
    {
        anchors.fill: parent
        radius: Style.radius
        color:
        {
            if (!control.enabled)
                return "transparent"
            if (control.tone == "danger" && control.hovered)
                return control.pressedState ? Style.dangerSoftHover : Style.dangerSoft
            if (control.checked)
                return Style.accentSoft
            if (mouse.pressed)
                return Style.surfacePressed
            return control.hovered ? Style.surfaceHover : "transparent"
        }
        Behavior on color { ColorAnimation { duration: Style.hoverMs } }
    }

    readonly property bool pressedState: mouse.pressed

    Icon
    {
        anchors.centerIn: parent
        name: control.iconName
        color:
        {
            if (!control.enabled)
                return Style.textDisabled
            if (control.tone == "danger" && control.hovered)
                return Style.danger
            if (control.checked || control.tone == "accent")
                return Style.accent
            return control.hovered ? Style.text : Style.textSecondary
        }
    }

    MouseArea
    {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: control.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: control.clicked()
    }

    HoverTip
    {
        area: mouse
        text: control.tooltip
    }
}
