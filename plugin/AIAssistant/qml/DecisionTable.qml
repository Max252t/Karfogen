import QtQuick 2.2
import "."

Column
{
    id: table
    property var txt: assistant.strings
    property var rows: []
    property bool showTitle: true
    readonly property bool stacked: width < Style.narrowWidth

    width: parent ? parent.width : implicitWidth
    spacing: Style.s3

    Text
    {
        visible: table.showTitle
        width: parent.width
        text: table.txt.decisions_title
        font: Style.smallStrong
        color: Style.textSecondary
    }

    Repeater
    {
        model: table.rows

        Item
        {
            width: table.width
            height: table.stacked ? label.height + Style.px(2) + body.height : Math.max(label.height, body.height)

            Text
            {
                id: label
                width: table.stacked ? parent.width : Math.round(parent.width * 0.3) - Style.s2
                text: modelData.label
                font: table.stacked ? Style.small : Style.body
                color: Style.textSecondary
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Column
            {
                id: body
                x: table.stacked ? 0 : Math.round(parent.width * 0.3)
                y: table.stacked ? label.height + Style.px(2) : 0
                width: parent.width - x
                spacing: Style.px(2)

                Text
                {
                    width: parent.width
                    text: modelData.value != "" ? modelData.value : "—"
                    font: Style.bodyStrong
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Text
                {
                    width: parent.width
                    visible: modelData.reason != ""
                    text: table.txt.why + ": " + modelData.reason
                    font: Style.small
                    color: Style.textSecondary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }
        }
    }
}
