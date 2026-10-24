import QtQuick 2.2
import QtQuick.Controls.Private 1.0

// Shows the native tooltip for a MouseArea we already own; a second hover MouseArea on top
// (as the slicer's tooltip area adds) would steal the pointing-hand cursor from the button.
Timer
{
    id: tip
    property var area: null
    property string text: ""

    interval: 600
    running: area !== null && area.containsMouse && !area.pressed && text != ""
    onTriggered: Tooltip.showText(area, Qt.point(area.mouseX, area.mouseY), text)
    onRunningChanged: if (!running) Tooltip.hideText()
}
