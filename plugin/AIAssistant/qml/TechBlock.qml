import QtQuick 2.2
import QtQuick.Controls 1.1
import "."

Rectangle
{
    id: block
    property var txt: assistant.strings
    property string text: ""
    property string label: ""
    readonly property int textHeight: code.contentHeight + 2 * Style.s3

    width: parent ? parent.width : implicitWidth
    height: header.height + Math.min(textHeight, Style.techMaxHeight)
    radius: Style.radius
    color: Style.codeBackground

    Item
    {
        id: header
        width: parent.width
        height: Style.controlSmall

        Text
        {
            anchors.left: parent.left
            anchors.leftMargin: Style.s3
            anchors.right: copy.left
            anchors.verticalCenter: parent.verticalCenter
            text: block.label
            font: Style.caption
            color: Style.textMuted
            elide: Text.ElideRight
        }

        AButton
        {
            id: copy
            anchors.right: parent.right
            anchors.rightMargin: Style.px(2)
            anchors.verticalCenter: parent.verticalCenter
            size: "small"
            variant: "ghost"
            iconName: "copy"
            iconOnly: true
            text: block.txt.copy
            onClicked: assistant.copyText(block.text)
        }
    }

    ScrollView
    {
        id: scroll
        anchors.top: header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        style: Style.scrollStyle
        horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff
        verticalScrollBarPolicy: block.textHeight > Style.techMaxHeight ? Qt.ScrollBarAsNeeded : Qt.ScrollBarAlwaysOff

        Item
        {
            width: scroll.viewport.width
            height: code.contentHeight + Style.s3

            TextEdit
            {
                id: code
                x: Style.s3
                width: parent.width - 2 * Style.s3
                text: block.text
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.WrapAnywhere
                textFormat: TextEdit.PlainText
                font: Style.mono
                color: Style.textSecondary
                selectionColor: Style.accent
            }
        }
    }
}
