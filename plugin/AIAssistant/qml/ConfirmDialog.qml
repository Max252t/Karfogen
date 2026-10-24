import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Window 2.2
import UM 1.2 as UM
import "."

Window
{
    id: dialog
    property var txt: assistant.strings
    property string message: ""
    property string confirmText: ""
    property string checkText: ""
    property string checkHint: ""
    property bool checked: false
    property bool danger: false
    signal confirmed(bool checked)

    function ask()
    {
        check.checked = dialog.checked
        dialog.visible = true
        dialog.requestActivate()
        confirmButton.forceActiveFocus()
    }

    function finish(accepted)
    {
        dialog.visible = false
        if (accepted)
            dialog.confirmed(check.checked)
    }

    modality: Qt.WindowModal
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    width: Math.round(420 * Style.scale)
    height: body.height + buttons.height + 3 * Style.margin
    minimumWidth: width
    maximumWidth: width
    minimumHeight: height
    maximumHeight: height
    color: Style.background

    Item
    {
        anchors.fill: parent
        focus: true
        Keys.onEscapePressed: dialog.finish(false)

        Column
        {
            id: body
            x: Style.margin
            y: Style.margin
            width: parent.width - 2 * Style.margin
            spacing: Style.narrow

            Text
            {
                width: parent.width
                text: dialog.title
                font: Style.fontHeading
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Text
            {
                width: parent.width
                text: dialog.message
                font: Style.font
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            CheckRow
            {
                id: check
                visible: dialog.checkText != ""
                text: dialog.checkText
                secondary: dialog.checkHint
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
                text: dialog.txt.cancel
                onClicked: dialog.finish(false)
            }

            AButton
            {
                id: confirmButton
                variant: dialog.danger ? "danger" : "primary"
                text: dialog.confirmText
                onClicked: dialog.finish(true)
            }
        }
    }
}
