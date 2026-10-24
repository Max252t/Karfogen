import QtQuick 2.2
import "."

Icon
{
    id: spinner
    property bool running: visible
    name: "spinner"
    color: Style.accent

    RotationAnimation on rotation
    {
        from: 0
        to: 360
        duration: 900
        loops: Animation.Infinite
        running: spinner.running
    }
}
