import QtQuick 2.2
import "."

Column
{
    id: list
    property var txt: assistant.strings
    property var stages: []
    property var openStages: ({})
    property var openTech: ({})

    width: parent ? parent.width : implicitWidth
    spacing: Style.px(2)

    function toggle(map, key)
    {
        var copy = {}
        for (var k in map)
            copy[k] = map[k]
        copy[key] = !copy[key]
        return copy
    }

    Repeater
    {
        model: list.stages

        Column
        {
            id: stage
            property bool open: list.openStages[index] === true
            property bool techOpen: list.openTech[index] === true
            property bool hasMore: modelData.facts.length > 0 || modelData.details != "" || modelData.fixed

            width: list.width
            spacing: Style.s2

            Item
            {
                id: row
                width: parent.width
                height: Style.controlSmall
                activeFocusOnTab: stage.hasMore
                Keys.onSpacePressed: list.openStages = list.toggle(list.openStages, index)
                Keys.onReturnPressed: list.openStages = list.toggle(list.openStages, index)

                Rectangle
                {
                    anchors.fill: parent
                    anchors.leftMargin: -Style.s2
                    anchors.rightMargin: -Style.s2
                    radius: Style.radius
                    color: rowMouse.containsMouse ? Style.surfaceAlt : "transparent"
                    border.width: row.activeFocus ? Style.focusWidth : 0
                    border.color: Style.focusRing
                    Behavior on color { ColorAnimation { duration: Style.hoverMs } }
                }

                Spinner
                {
                    id: spinner
                    anchors.verticalCenter: parent.verticalCenter
                    size: Style.iconSmall
                    visible: modelData.status == "running"
                }

                Icon
                {
                    anchors.verticalCenter: parent.verticalCenter
                    size: Style.iconSmall
                    visible: modelData.status != "running"
                    name: modelData.status == "error" ? "alert" : "check"
                    color: modelData.status == "error" ? Style.danger : Style.success
                }

                Text
                {
                    id: title
                    anchors.left: spinner.right
                    anchors.leftMargin: Style.s2
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(implicitWidth, row.width * 0.6)
                    text: modelData.title + (modelData.status == "running" ? "…" : "")
                    font: modelData.status == "running" ? Style.bodyStrong : Style.body
                    color: modelData.status == "error" ? Style.danger : Style.text
                    elide: Text.ElideRight
                }

                Text
                {
                    anchors.left: title.right
                    anchors.leftMargin: Style.s2
                    anchors.right: chevron.left
                    anchors.rightMargin: Style.s1
                    anchors.verticalCenter: parent.verticalCenter
                    text: modelData.summary
                    font: Style.small
                    color: modelData.status == "error" ? Style.danger : Style.textMuted
                    elide: Text.ElideRight
                }

                Icon
                {
                    id: chevron
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    visible: stage.hasMore
                    name: stage.open ? "chevron-down" : "chevron-right"
                    size: Style.iconSmall
                    color: rowMouse.containsMouse || stage.open ? Style.textSecondary : Style.textMuted
                }

                MouseArea
                {
                    id: rowMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: stage.hasMore ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: if (stage.hasMore) list.openStages = list.toggle(list.openStages, index)
                }

                HoverTip
                {
                    area: rowMouse
                    text: stage.hasMore ? (stage.open ? list.txt.hide_details : list.txt.details) : ""
                }
            }

            Column
            {
                visible: stage.open
                x: Style.iconSmall + Style.s2
                width: parent.width - x
                spacing: Style.s2

                Text
                {
                    visible: modelData.fixed
                    width: parent.width
                    text: list.txt.fixed_after_error
                    font: Style.small
                    color: Style.warning
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Repeater
                {
                    model: stage.open ? modelData.facts : []

                    KeyValue
                    {
                        width: parent.width
                        key: modelData.label
                        value: modelData.value
                        keyShare: 0.42
                    }
                }

                AButton
                {
                    visible: modelData.details != ""
                    size: "small"
                    variant: "link"
                    iconName: stage.techOpen ? "chevron-down" : "chevron-right"
                    text: list.txt.tech_details
                    onClicked: list.openTech = list.toggle(list.openTech, index)
                }

                Loader
                {
                    width: parent.width
                    active: stage.open && stage.techOpen
                    visible: active
                    sourceComponent: TechBlock
                    {
                        text: modelData.details
                        label: list.txt.tech_details
                    }
                }
            }
        }
    }
}
