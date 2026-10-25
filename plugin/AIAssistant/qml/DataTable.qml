import QtQuick 2.2
import "."

Item
{
    id: table
    property var header: []
    property var rows: []
    readonly property int columns: Math.max(1, header.length)
    readonly property bool stacked: width < columns * Style.px(130)
    readonly property real cellWidth: width / columns

    width: parent ? parent.width : implicitWidth
    height: stacked ? cards.height : grid.height

    function linkClicked(link)
    {
        if (link.indexOf("http://") == 0 || link.indexOf("https://") == 0)
            Qt.openUrlExternally(link)
    }

    Column
    {
        id: grid
        visible: !table.stacked
        width: parent.width

        Repeater
        {
            model: table.stacked ? [] : [table.header].concat(table.rows)

            Item
            {
                id: line
                property var cells: modelData
                property bool head: index == 0
                width: grid.width
                height: cellRow.height + Style.s2 * 2

                Row
                {
                    id: cellRow
                    y: Style.s2

                    Repeater
                    {
                        model: line.cells

                        Text
                        {
                            width: table.cellWidth - (index < table.columns - 1 ? Style.s2 : 0)
                            text: modelData
                            textFormat: Text.RichText
                            font: line.head ? Style.smallStrong : Style.body
                            color: line.head ? Style.textSecondary : Style.text
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            onLinkActivated: table.linkClicked(link)
                        }
                    }
                }

                Rectangle
                {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: Style.line
                    color: Style.border
                    visible: index < table.rows.length
                }
            }
        }
    }

    Column
    {
        id: cards
        visible: table.stacked
        width: parent.width
        spacing: Style.s2

        Repeater
        {
            model: table.stacked ? table.rows : []

            Rectangle
            {
                id: card
                property var cells: modelData
                width: cards.width
                height: cardColumn.height + 2 * Style.s3
                radius: Style.radius
                color: Style.surfaceAlt

                Column
                {
                    id: cardColumn
                    x: Style.s3
                    y: Style.s3
                    width: parent.width - 2 * Style.s3
                    spacing: Style.s1

                    Repeater
                    {
                        model: card.cells

                        Column
                        {
                            width: cardColumn.width
                            visible: modelData != ""

                            Text
                            {
                                width: parent.width
                                text: index < table.header.length ? table.header[index] : ""
                                textFormat: Text.RichText
                                font: Style.caption
                                color: Style.textMuted
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }

                            Text
                            {
                                width: parent.width
                                text: modelData
                                textFormat: Text.RichText
                                font: Style.body
                                color: Style.text
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                onLinkActivated: table.linkClicked(link)
                            }
                        }
                    }
                }
            }
        }
    }
}
