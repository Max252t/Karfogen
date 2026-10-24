import QtQuick 2.2
import "."

Item
{
    id: row
    property string key: ""
    property string value: ""
    property string secondary: ""
    property string note: ""
    property real keyShare: 0.38

    width: parent ? parent.width : implicitWidth
    height: Math.max(keyLabel.height, valueColumn.height)

    Text
    {
        id: keyLabel
        width: Math.round(row.width * row.keyShare) - Style.s2
        text: row.key
        font: Style.body
        color: Style.textSecondary
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }

    Column
    {
        id: valueColumn
        anchors.left: keyLabel.right
        anchors.leftMargin: Style.s2
        anchors.right: parent.right
        spacing: Style.px(2)

        Text
        {
            width: parent.width
            text: row.value != "" ? row.value : "—"
            font: Style.bodyStrong
            color: row.value != "" ? Style.text : Style.textMuted
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Text
        {
            width: parent.width
            visible: row.note != ""
            text: row.note
            font: Style.small
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Text
        {
            width: parent.width
            visible: row.secondary != ""
            text: row.secondary
            font: Style.caption
            color: Style.textMuted
            wrapMode: Text.WrapAnywhere
        }
    }
}
