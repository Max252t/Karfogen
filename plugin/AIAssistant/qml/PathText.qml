import QtQuick 2.2
import "."

Text
{
    id: pathText
    property var txt: assistant.strings
    property string path: ""

    text: pathText.path
    font: Style.small
    color: mouse.containsMouse ? Style.accent : Style.textSecondary
    elide: Text.ElideMiddle

    MouseArea
    {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: assistant.copyText(pathText.path)
    }

    HoverTip
    {
        area: mouse
        text: pathText.path + "\n" + pathText.txt.copy
    }
}
