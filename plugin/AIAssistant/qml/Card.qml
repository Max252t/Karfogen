import QtQuick 2.2
import "."

Rectangle
{
    id: card
    default property alias content: inner.children
    property int inset: Style.s4
    property int spacing: Style.s3
    property bool outlined: false

    width: parent ? parent.width : implicitWidth
    height: inner.height + 2 * inset
    radius: Style.radiusLarge
    color: Style.surface
    border.width: outlined ? Style.line : 0
    border.color: Style.border

    Column
    {
        id: inner
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: card.inset
        spacing: card.spacing
    }
}
