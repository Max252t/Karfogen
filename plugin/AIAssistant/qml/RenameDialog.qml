import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Window 2.2
import UM 1.2 as UM
import "."

Window
{
    id: dialog
    property var txt: assistant.strings
    property string original: ""
    signal accepted(string name)

    function ask(name)
    {
        dialog.original = name
        field.text = name
        dialog.visible = true
        dialog.requestActivate()
        field.forceActiveFocus()
        field.selectAll()
    }

    function finish(save)
    {
        var name = field.text.replace(/^\s+|\s+$/g, "")
        if (save && name == "")
            return
        dialog.visible = false
        if (save && name != dialog.original)
            dialog.accepted(name)
    }

    title: txt.proj_rename_title
    modality: Qt.WindowModal
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    width: Math.round(400 * Style.scale)
    height: column.height + buttons.height + 3 * Style.margin
    minimumWidth: width
    maximumWidth: width
    minimumHeight: height
    maximumHeight: height
    color: Style.background

    Item
    {
        anchors.fill: parent
        Keys.onEscapePressed: dialog.finish(false)

        Column
        {
            id: column
            x: Style.margin
            y: Style.margin
            width: parent.width - 2 * Style.margin
            spacing: Style.narrow

            Text
            {
                text: txt.proj_name
                font: Style.font
                color: Style.textSecondary
            }

            TextField
            {
                id: field
                width: parent.width
                height: Style.controlHeight
                maximumLength: 80
                placeholderText: txt.proj_name_placeholder
                style: UM.Theme.styles.text_field
                property string unit: ""
                Keys.onReturnPressed: dialog.finish(true)
                Keys.onEnterPressed: dialog.finish(true)
                Keys.onEscapePressed: dialog.finish(false)
            }
        }

        Row
        {
            id: buttons
            anchors.right: parent.right
            anchors.rightMargin: Style.margin
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.margin
            spacing: Style.narrow

            AButton
            {
                text: txt.cancel
                onClicked: dialog.finish(false)
            }

            AButton
            {
                variant: "primary"
                text: txt.save
                enabled: field.text.replace(/\s/g, "") != ""
                onClicked: dialog.finish(true)
            }
        }
    }
}
