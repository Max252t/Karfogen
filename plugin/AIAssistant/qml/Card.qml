import QtQuick 2.2
import "."

Rectangle
{
    id: card
    default property alias content: inner.children
    property int inset: Style.margin
    property color accent: "transparent"
    property bool tinted: false

    width: parent ? parent.width : implicitWidth
    height: inner.height + 2 * inset
    radius: Style.radius
    color: tinted ? Style.panel : Style.background
    border.width: Style.lineWidth
    border.color: Style.hairline

    Rectangle
    {
        visible: card.accent.a > 0
        width: Math.round(3 * Style.scale)
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        color: card.accent
    }

    Column
    {
        id: inner
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: card.inset
        spacing: Style.narrow
    }
}
