import QtQuick 2.2
import "."

Column
{
    id: rich
    property var blocks: []
    property color textColor: Style.text

    width: parent ? parent.width : implicitWidth
    spacing: Style.s2 + Style.px(2)

    function linkClicked(link)
    {
        if (link.indexOf("http://") == 0 || link.indexOf("https://") == 0)
            Qt.openUrlExternally(link)
    }

    Repeater
    {
        model: rich.blocks

        Loader
        {
            property var block: modelData
            width: rich.width
            sourceComponent:
            {
                switch (modelData.type)
                {
                    case "heading": return headingComponent
                    case "list": return listComponent
                    case "table": return tableComponent
                    case "code": return codeComponent
                    default: return paragraphComponent
                }
            }
        }
    }

    Component
    {
        id: paragraphComponent

        TextEdit
        {
            width: parent ? parent.width : 0
            text: parent ? parent.block.text : ""
            textFormat: TextEdit.RichText
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            font: Style.reading
            color: rich.textColor
            selectionColor: Style.accent
            onLinkActivated: rich.linkClicked(link)
        }
    }

    Component
    {
        id: headingComponent

        TextEdit
        {
            width: parent ? parent.width : 0
            text: parent ? parent.block.text : ""
            textFormat: TextEdit.RichText
            readOnly: true
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            font: parent && parent.block.level <= 2 ? Style.title : Style.bodyStrong
            color: Style.text
            selectionColor: Style.accent
        }
    }

    Component
    {
        id: listComponent

        Column
        {
            id: listColumn
            property var items: parent ? parent.block.items : []
            width: parent ? parent.width : 0
            spacing: Style.s1

            Repeater
            {
                model: listColumn.items

                Item
                {
                    width: listColumn.width
                    height: Math.max(marker.height, itemText.height)

                    Text
                    {
                        id: marker
                        x: modelData.level * Style.s4
                        width: Style.s4 + (modelData.marker.length > 1 ? Style.s2 : 0)
                        text: modelData.marker
                        font: Style.reading
                        color: Style.textSecondary
                    }

                    TextEdit
                    {
                        id: itemText
                        anchors.left: marker.right
                        anchors.right: parent.right
                        text: modelData.text
                        textFormat: TextEdit.RichText
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        font: Style.reading
                        color: rich.textColor
                        selectionColor: Style.accent
                        onLinkActivated: rich.linkClicked(link)
                    }
                }
            }
        }
    }

    Component
    {
        id: tableComponent

        DataTable
        {
            width: parent ? parent.width : 0
            header: parent ? parent.block.header : []
            rows: parent ? parent.block.rows : []
        }
    }

    Component
    {
        id: codeComponent

        TechBlock
        {
            width: parent ? parent.width : 0
            text: parent ? parent.block.text : ""
            label: parent ? parent.block.lang : ""
        }
    }
}
