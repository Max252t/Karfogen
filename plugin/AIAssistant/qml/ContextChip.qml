import QtQuick 2.2
import "."

Rectangle
{
    id: chip
    property string kind: "model"
    property string title: ""
    property string subtitle: ""
    property string thumbnail: ""
    property bool selected: true
    property bool removable: true
    property bool expandable: false
    property bool expanded: false
    property string removeTip: ""
    property string tooltip: ""
    property int maxWidth: Style.px(260)
    signal clicked()
    signal removed()

    readonly property bool interactive: !removable

    width: Math.min(content.implicitWidth + Style.s2 + (removable ? Style.controlSmall : Style.s3), maxWidth)
    height: Style.px(44)
    radius: Style.radius
    readonly property bool highlighted: selected && interactive
    color: highlighted ? Style.accentSoft : (mouse.containsMouse && interactive ? Style.surfaceHover : Style.surface)
    border.width: Style.line
    border.color: highlighted ? Style.accent : (mouse.containsMouse ? Style.borderStrong : Style.border)

    Row
    {
        id: content
        x: Style.s1 + Style.px(2)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.s2

        Rectangle
        {
            width: Style.px(32)
            height: width
            radius: Style.radiusSmall
            color: chip.highlighted ? Style.surface : (chip.kind == "image" ? Style.surfaceAlt : Style.accentSoft)
            clip: true
            anchors.verticalCenter: parent.verticalCenter

            Image
            {
                anchors.fill: parent
                visible: chip.thumbnail != ""
                source: chip.thumbnail
                sourceSize.width: width * 2
                sourceSize.height: height * 2
                fillMode: Image.PreserveAspectCrop
                asynchronous: true
            }

            Icon
            {
                anchors.centerIn: parent
                visible: chip.thumbnail == ""
                name: chip.interactive ? (chip.selected ? "check" : "plus") : (chip.kind == "image" ? "image" : "cube")
                color: chip.selected || !chip.interactive ? Style.accent : Style.textSecondary
            }
        }

        Column
        {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.min(Math.max(titleText.implicitWidth, subtitleText.implicitWidth),
                            chip.maxWidth - Style.px(32) - 3 * Style.s2 - (chip.removable ? Style.controlSmall : Style.s3)
                            - (chip.expandable ? Style.iconSmall + Style.s1 : 0))

            Text
            {
                id: titleText
                width: parent.width
                text: chip.title
                font: Style.smallStrong
                color: chip.highlighted ? Style.accent : Style.text
                elide: Text.ElideMiddle
            }

            Text
            {
                id: subtitleText
                width: parent.width
                visible: text != ""
                text: chip.subtitle
                font: Style.caption
                color: Style.textMuted
                elide: Text.ElideRight
            }
        }

        Icon
        {
            visible: chip.expandable
            anchors.verticalCenter: parent.verticalCenter
            name: chip.expanded ? "chevron-down" : "chevron-right"
            size: Style.iconSmall
        }
    }

    MouseArea
    {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: chip.interactive ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: if (chip.interactive) chip.clicked()
    }

    HoverTip
    {
        area: mouse
        text: chip.tooltip != "" ? chip.tooltip : (titleText.truncated ? chip.title : "")
    }

    IconButton
    {
        visible: chip.removable
        anchors.right: parent.right
        anchors.rightMargin: Style.px(2)
        anchors.verticalCenter: parent.verticalCenter
        width: Style.controlSmall
        height: Style.controlSmall
        iconName: "x"
        tooltip: chip.removeTip
        onClicked: chip.removed()
    }
}
