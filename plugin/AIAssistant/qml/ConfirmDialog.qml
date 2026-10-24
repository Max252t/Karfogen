import QtQuick 2.2
import QtQuick.Window 2.2
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
    width: Style.px(440)
    height: body.height + buttons.height + 3 * Style.s4
    minimumWidth: width
    maximumWidth: width
    minimumHeight: height
    maximumHeight: height
    color: Style.surface

    Item
    {
        anchors.fill: parent
        focus: true
        Keys.onEscapePressed: dialog.finish(false)

        Column
        {
            id: body
            x: Style.s4
            y: Style.s4
            width: parent.width - 2 * Style.s4
            spacing: Style.s3

            Row
            {
                width: parent.width
                spacing: Style.s3

                Rectangle
                {
                    width: Style.px(32)
                    height: width
                    radius: Style.radius
                    color: dialog.danger ? Style.dangerSoft : Style.accentSoft

                    Icon
                    {
                        anchors.centerIn: parent
                        name: dialog.danger ? "warning" : "info"
                        color: dialog.danger ? Style.danger : Style.accent
                    }
                }

                Text
                {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - Style.px(32) - Style.s3
                    text: dialog.title
                    font: Style.title
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }

            Text
            {
                width: parent.width
                text: dialog.message
                font: Style.body
                color: Style.textSecondary
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
            anchors.rightMargin: Style.s4
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.s4
            spacing: Style.s2

            AButton
            {
                variant: "ghost"
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
