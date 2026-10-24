import QtQuick 2.2
import UM 1.2 as UM
import "."

UM.RecolorImage
{
    property string name: ""
    property int size: Style.iconSize

    width: size
    height: size
    sourceSize.width: size * 2
    sourceSize.height: size * 2
    source: name != "" ? Qt.resolvedUrl("icons/" + name + ".svg") : ""
    color: Style.textSecondary
}
