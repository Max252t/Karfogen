import QtQuick 2.2
import "."

Item
{
    id: section
    property string text: ""
    property string hint: ""
    property string badge: ""

    width: parent ? parent.width : implicitWidth
    height: column.height

    Column
    {
        id: column
        width: parent.width
        spacing: Style.px(2)

        Row
        {
            spacing: Style.s2

            Text
            {
                text: section.text
                font: Style.title
                color: Style.text
                elide: Text.ElideRight
                width: Math.min(implicitWidth, section.width - badgeText.width - Style.s2)
            }

            Text
            {
                id: badgeText
                anchors.baseline: parent.children[0].baseline
                visible: section.badge != "" && section.badge != "0"
                text: section.badge
                font: Style.small
                color: Style.textMuted
            }
        }

        Text
        {
            width: parent.width
            visible: section.hint != ""
            text: section.hint
            font: Style.small
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }
    }
}
