import QtQuick 2.2
import "."

Column
{
    id: list
    property var txt: assistant.strings
    property var changes: []
    property string countText: ""
    property bool showTitle: true
    readonly property bool stacked: width < Style.narrowWidth

    width: parent ? parent.width : implicitWidth
    spacing: Style.s2

    Text
    {
        visible: list.showTitle
        width: parent.width
        text: list.txt.params_title + (list.countText != "" ? " · " + list.countText : "")
        font: Style.smallStrong
        color: Style.textSecondary
        elide: Text.ElideRight
    }

    Repeater
    {
        model: list.changes

        Item
        {
            width: list.width
            height: list.stacked ? label.height + Style.px(2) + values.height
                                 : Math.max(label.height, values.height)

            Text
            {
                id: label
                width: list.stacked ? parent.width : Math.round(parent.width * 0.5) - Style.s2
                text: modelData.label
                font: Style.body
                color: Style.textSecondary
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Text
            {
                id: values
                x: list.stacked ? 0 : Math.round(parent.width * 0.5)
                y: list.stacked ? label.height + Style.px(2) : 0
                width: list.stacked ? parent.width : parent.width - x
                horizontalAlignment: list.stacked ? Text.AlignLeft : Text.AlignRight
                textFormat: Text.StyledText
                text: (modelData.old != "" ? "<font color='" + Style.textMuted + "'>" + modelData.old.replace(/&/g, "&amp;").replace(/</g, "&lt;")
                                            + "</font>&nbsp;→&nbsp;" : "")
                      + "<b>" + modelData.value.replace(/&/g, "&amp;").replace(/</g, "&lt;") + "</b>"
                font: Style.body
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            MouseArea
            {
                id: rowMouse
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.NoButton
            }

            HoverTip
            {
                area: rowMouse
                text: modelData.key != modelData.label ? modelData.key : ""
            }
        }
    }
}
