import QtQuick 2.2
import "."

Rectangle
{
    id: segmented
    property var options: []
    property string current: ""
    signal selected(string value)

    implicitWidth: row.implicitWidth + 2 * Style.px(3)
    implicitHeight: Style.controlSmall
    radius: Style.radius
    color: Style.surfaceAlt

    Row
    {
        id: row
        anchors.centerIn: parent
        spacing: Style.px(2)

        Repeater
        {
            model: segmented.options

            Item
            {
                id: option
                property bool active: segmented.current == modelData.value
                width: optionText.implicitWidth + 2 * Style.s3
                height: segmented.height - 2 * Style.px(3)
                activeFocusOnTab: true
                Keys.onSpacePressed: segmented.selected(modelData.value)
                Keys.onReturnPressed: segmented.selected(modelData.value)
                Keys.onLeftPressed: if (index > 0) segmented.selected(segmented.options[index - 1].value)
                Keys.onRightPressed: if (index < segmented.options.length - 1) segmented.selected(segmented.options[index + 1].value)

                Rectangle
                {
                    anchors.fill: parent
                    radius: Style.radiusSmall
                    color: option.active ? Style.surface : (optionMouse.containsMouse ? Style.surfaceHover : "transparent")
                    border.width: option.activeFocus ? Style.focusWidth : (option.active ? Style.line : 0)
                    border.color: option.activeFocus ? Style.focusRing : Style.border
                    Behavior on color { ColorAnimation { duration: Style.hoverMs } }
                }

                Text
                {
                    id: optionText
                    anchors.centerIn: parent
                    text: modelData.label
                    font: option.active ? Style.smallStrong : Style.small
                    color: option.active ? Style.text : Style.textSecondary
                }

                MouseArea
                {
                    id: optionMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: segmented.selected(modelData.value)
                }

                HoverTip
                {
                    area: optionMouse
                    text: modelData.hint || ""
                }
            }
        }
    }
}
