import QtQuick 2.2
import UM 1.2 as UM
import "."

UM.RecolorImage
{
    id: spinner
    property bool running: visible
    width: Style.smallIcon
    height: Style.smallIcon
    sourceSize.width: width
    sourceSize.height: height
    source: UM.Theme.getIcon("rotate")
    color: Style.primary

    RotationAnimation on rotation
    {
        from: 0
        to: 360
        duration: 1200
        loops: Animation.Infinite
        running: spinner.running
    }
}
