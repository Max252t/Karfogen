import QtQuick 2.2
import "."

Rectangle
{
    id: line
    property real value: 0
    property bool indeterminate: false
    property string tone: "accent"
    readonly property color fill: tone == "danger" ? Style.danger : (tone == "muted" ? Style.textMuted
                                  : (tone == "success" ? Style.success : Style.accent))

    width: parent ? parent.width : implicitWidth
    height: Style.px(4)
    radius: height / 2
    color: Style.surfaceAlt
    clip: true

    Rectangle
    {
        visible: !line.indeterminate
        height: parent.height
        radius: parent.radius
        width: Math.max(line.value > 0 ? parent.height : 0, Math.round(parent.width * Math.max(0, Math.min(1, line.value))))
        color: line.fill
        Behavior on width { NumberAnimation { duration: Style.progressMs; easing.type: Easing.OutCubic } }
    }

    Rectangle
    {
        id: runner
        visible: line.indeterminate
        height: parent.height
        radius: parent.radius
        width: Math.round(parent.width * 0.28)
        color: line.fill
        opacity: 0.8

        SequentialAnimation on x
        {
            running: line.indeterminate && line.visible && Style.motion
            loops: Animation.Infinite
            NumberAnimation { from: -runner.width; to: line.width; duration: 1400; easing.type: Easing.InOutQuad }
            PauseAnimation { duration: 200 }
        }
    }
}
