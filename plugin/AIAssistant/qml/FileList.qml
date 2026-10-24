import QtQuick 2.2
import "."

Column
{
    id: files
    property var txt: assistant.strings
    property var items: []

    width: parent ? parent.width : implicitWidth
    spacing: Style.s2

    Text
    {
        width: parent.width
        text: files.txt.files_title
        font: Style.smallStrong
        color: Style.textSecondary
    }

    Repeater
    {
        model: files.items

        Item
        {
            width: files.width
            height: Math.max(Style.controlSmall, texts.height)

            Icon
            {
                id: icon
                y: Style.px(2)
                name: "file"
                color: Style.accent
            }

            Column
            {
                id: texts
                anchors.left: icon.right
                anchors.leftMargin: Style.s2
                anchors.right: copy.left
                anchors.rightMargin: Style.s2
                spacing: Style.px(1)

                Text
                {
                    width: parent.width
                    text: modelData.label + " · " + modelData.name
                    font: Style.bodyStrong
                    color: Style.text
                    elide: Text.ElideRight
                }

                PathText
                {
                    width: parent.width
                    path: modelData.path
                }
            }

            AButton
            {
                id: copy
                anchors.right: parent.right
                size: "small"
                variant: "ghost"
                iconName: "copy"
                iconOnly: true
                text: files.txt.copy
                onClicked: assistant.copyText(modelData.path)
            }
        }
    }

    AButton
    {
        size: "small"
        variant: "link"
        iconName: "folder"
        text: files.txt.res_open_folder
        onClicked: assistant.openResultsFolder()
    }
}
