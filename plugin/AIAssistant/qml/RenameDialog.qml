import QtQuick 2.2
import QtQuick.Window 2.2
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
    width: Style.px(420)
    height: column.height + buttons.height + 3 * Style.s4
    minimumWidth: width
    maximumWidth: width
    minimumHeight: height
    maximumHeight: height
    color: Style.surface

    Item
    {
        anchors.fill: parent
        Keys.onEscapePressed: dialog.finish(false)

        Column
        {
            id: column
            x: Style.s4
            y: Style.s4
            width: parent.width - 2 * Style.s4
            spacing: Style.s2

            Text
            {
                text: txt.proj_rename_title
                font: Style.title
                color: Style.text
            }

            Text
            {
                text: txt.proj_name
                font: Style.small
                color: Style.textSecondary
            }

            Field
            {
                id: field
                width: parent.width
                maximumLength: 80
                placeholder: txt.proj_name_placeholder
                invalid: field.text.replace(/\s/g, "") == ""
                onAccepted: dialog.finish(true)
            }
        }

        Row
        {
            id: buttons
            anchors.right: parent.right
            anchors.rightMargin: Style.s4
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.s4
            spacing: Style.s2

            AButton
            {
                variant: "ghost"
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
