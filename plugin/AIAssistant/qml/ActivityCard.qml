import QtQuick 2.2
import "."

Rectangle
{
    id: card
    property var txt: assistant.strings
    property string phase: "running"
    property string title: ""
    property real progress: 0
    property int percent: 0
    property bool indeterminate: false
    property var stages: []
    property string stageCount: ""
    property string summary: ""
    property var metrics: []
    property var changes: []
    property var decisions: []
    property var exports: []
    property string impact: ""
    property string actions: ""
    property bool serious: false
    property string liveText: ""
    property bool historyOpen: false
    property bool moreOpen: false

    readonly property bool active: phase == "running" || phase == "stopping"
    readonly property bool finished: phase == "done"
    readonly property bool failed: phase == "error"
    readonly property bool cancelled: phase == "cancelled"
    readonly property bool hasResult: metrics.length > 0 || exports.length > 0
    readonly property bool hasMore: changes.length > 0 || decisions.length > 0 || exports.length > 0 || stages.length > 0

    width: parent ? parent.width : implicitWidth
    height: column.height + 2 * Style.s3 + Style.px(2)
    radius: Style.radiusLarge
    color: Style.surface

    Column
    {
        id: column
        x: Style.s4
        y: Style.s3 + Style.px(1)
        width: parent.width - 2 * Style.s4
        spacing: Style.s2

        Item
        {
            id: header
            width: parent.width
            height: Math.max(Style.iconSize, titleText.height)

            Spinner
            {
                id: spinner
                anchors.verticalCenter: parent.verticalCenter
                visible: card.active
                running: visible
            }

            Icon
            {
                anchors.verticalCenter: parent.verticalCenter
                visible: !card.active
                name: card.finished ? "check-circle" : (card.cancelled ? "stop-circle" : "alert")
                color: card.finished ? Style.success : (card.cancelled ? Style.textSecondary : Style.danger)
            }

            Text
            {
                id: titleText
                anchors.left: spinner.right
                anchors.leftMargin: Style.s2
                anchors.right: percentText.left
                anchors.rightMargin: Style.s2
                anchors.verticalCenter: parent.verticalCenter
                text: card.title
                font: Style.bodyStrong
                color: Style.text
                elide: Text.ElideRight
            }

            Text
            {
                id: percentText
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                visible: !card.finished && !card.indeterminate
                text: "≈ " + card.percent + " %"
                font: Style.small
                color: Style.textSecondary

                MouseArea
                {
                    id: percentMouse
                    anchors.fill: parent
                    anchors.margins: -Style.s1
                    hoverEnabled: true
                    acceptedButtons: Qt.NoButton
                }

                HoverTip
                {
                    area: percentMouse
                    text: card.txt.prog_tip
                }
            }
        }

        ProgressLine
        {
            visible: !card.finished
            value: card.progress
            indeterminate: card.indeterminate
            tone: card.failed ? "danger" : (card.cancelled || card.phase == "stopping" ? "muted" : "accent")
        }

        Item
        {
            visible: card.active && card.liveText != ""
            width: parent.width
            height: visible ? liveLabel.height : 0

            Icon
            {
                id: liveIcon
                y: Math.round((liveLabel.height - height) / 2)
                name: "sparkle"
                size: Style.iconSmall
                color: Style.textMuted
            }

            Text
            {
                id: liveLabel
                anchors.left: liveIcon.right
                anchors.leftMargin: Style.s2
                anchors.right: parent.right
                text: card.liveText
                font: Style.small
                color: Style.textSecondary
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
        }

        Text
        {
            visible: card.finished && card.summary != ""
            width: parent.width
            text: card.summary
            font: Style.body
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        MetricsRow
        {
            visible: card.finished && card.metrics.length > 0
            items: card.metrics
        }

        Text
        {
            visible: card.impact != ""
            width: parent.width
            text: card.impact
            font: Style.small
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Item
        {
            id: footer
            width: parent.width
            height: Style.controlSmall
            visible: card.active || card.hasMore || card.hasResult || card.actions != ""

            Row
            {
                anchors.left: parent.left
                anchors.leftMargin: -Style.s2
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.s2

                AButton
                {
                    visible: card.finished && card.hasResult
                    size: "small"
                    variant: "secondary"
                    text: card.txt.work_show_result
                    onClicked: assistant.runAction("result")
                }

                AButton
                {
                    visible: card.actions != ""
                    size: "small"
                    variant: "primary"
                    text: card.txt.act_continue
                    enabled: !assistant.busy
                    tooltip: enabled ? "" : card.txt.busy_hint
                    onClicked: assistant.runAction("continue")
                }

                AButton
                {
                    visible: card.finished ? card.hasMore : card.stages.length > 0
                    size: "small"
                    variant: "ghost"
                    iconName: (card.finished ? card.moreOpen : card.historyOpen) ? "chevron-down" : "chevron-right"
                    text: card.finished ? (card.moreOpen ? card.txt.work_less : card.txt.work_more)
                                        : card.txt.work_history + (card.stageCount != "" ? " · " + card.stageCount : "")
                    onClicked:
                    {
                        if (card.finished)
                            card.moreOpen = !card.moreOpen
                        else
                            card.historyOpen = !card.historyOpen
                    }
                }
            }

        }

        Column
        {
            visible: !card.finished && card.historyOpen
            width: parent.width
            spacing: Style.s2

            StageList
            {
                stages: card.historyOpen ? card.stages : []
            }
        }

        Column
        {
            visible: card.finished && card.moreOpen
            width: parent.width
            spacing: Style.s4

            Rectangle
            {
                width: parent.width
                height: Style.line
                color: Style.border
            }

            DecisionTable
            {
                visible: card.decisions.length > 0
                rows: card.moreOpen ? card.decisions : []
            }

            ParamChanges
            {
                visible: card.changes.length > 0
                changes: card.moreOpen ? card.changes : []
                countText: card.changes.length > 0 ? assistant.countText(card.changes.length, "changes") : ""
            }

            FileList
            {
                visible: card.exports.length > 0
                items: card.moreOpen ? card.exports : []
            }

            Column
            {
                visible: card.stages.length > 0
                width: parent.width
                spacing: Style.s2

                Text
                {
                    width: parent.width
                    text: card.txt.work_log + (card.stageCount != "" ? " · " + card.stageCount : "")
                    font: Style.smallStrong
                    color: Style.textSecondary
                }

                StageList
                {
                    stages: card.moreOpen ? card.stages : []
                }
            }
        }
    }
}
