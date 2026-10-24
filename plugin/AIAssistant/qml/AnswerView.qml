import QtQuick 2.2
import "."

Column
{
    id: answer
    property var txt: assistant.strings
    property var blocks: []
    property string plain: ""
    property bool collapsible: false
    property bool expanded: false
    property color textColor: Style.text
    readonly property bool overflow: collapsible && content.height > Style.collapsedAnswer + Style.s5
    readonly property bool clipped: overflow && !expanded

    width: parent ? parent.width : implicitWidth
    spacing: Style.s1

    Item
    {
        id: viewport
        width: parent.width
        height: answer.clipped ? Style.collapsedAnswer : content.height
        clip: answer.clipped

        Behavior on height { NumberAnimation { duration: Style.revealMs; easing.type: Easing.OutCubic } }

        RichBlocks
        {
            id: content
            width: parent.width
            blocks: answer.blocks
            textColor: answer.textColor
        }

        Rectangle
        {
            visible: answer.clipped
            anchors.bottom: parent.bottom
            width: parent.width
            height: Style.px(56)
            gradient: Gradient
            {
                GradientStop { position: 0.0; color: Qt.rgba(Style.window.r, Style.window.g, Style.window.b, 0) }
                GradientStop { position: 1.0; color: Style.window }
            }
        }
    }

    Row
    {
        visible: answer.overflow
        spacing: Style.s2

        AButton
        {
            size: "small"
            variant: "link"
            iconName: answer.expanded ? "chevron-down" : "chevron-right"
            text: answer.expanded ? answer.txt.read_less : answer.txt.read_more
            onClicked: answer.expanded = !answer.expanded
        }

        AButton
        {
            size: "small"
            variant: "ghost"
            iconName: "copy"
            text: answer.txt.copy_text
            onClicked: assistant.copyText(answer.plain)
        }
    }
}
