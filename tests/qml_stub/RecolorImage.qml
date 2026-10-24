import QtQuick 2.2

Item
{
    property alias source: img.source
    property alias sourceSize: img.sourceSize
    property color color: "black"

    Image
    {
        id: img
        anchors.fill: parent
    }
}
