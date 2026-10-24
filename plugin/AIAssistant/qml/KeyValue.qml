import QtQuick 2.2
import "."

Item
{
    id: row
    property string key: ""
    property string value: ""
    property string secondary: ""
    property real keyShare: 0.4

    width: parent ? parent.width : implicitWidth
    height: Math.max(keyLabel.height, valueColumn.height)

    Text
    {
        id: keyLabel
        width: Math.round(row.width * row.keyShare) - Style.narrow
        text: row.key
        font: Style.font
        color: Style.textSecondary
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
    }

    Column
    {
        id: valueColumn
        anchors.left: keyLabel.right
        anchors.leftMargin: Style.narrow
        anchors.right: parent.right

        Text
        {
            width: parent.width
            text: row.value != "" ? row.value : "—"
            font: Style.fontBold
            color: Style.text
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Text
        {
            width: parent.width
            visible: row.secondary != ""
            text: row.secondary
            font: Style.fontSmall
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }
    }
}
