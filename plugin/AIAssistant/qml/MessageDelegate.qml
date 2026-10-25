import QtQuick 2.2
import "."

Item
{
    id: entry
    property var txt: assistant.strings
    property bool expanded: false
    property string metaText: model.meta
    property string actionsText: model.actions
    property string kindText: model.kind
    readonly property int inset: Math.max(Style.s4, Math.round((width - Style.readableWidth) / 2))
    readonly property int contentWidth: Math.max(0, width - 2 * inset)
    readonly property bool hidden: kindText == "activity" && model.phase == "quiet"

    visible: !hidden
    height: hidden ? 0 : loader.y + loader.height + Style.s2

    function actionList()
    {
        return entry.actionsText ? entry.actionsText.split(",") : []
    }

    function fileIcon(kind)
    {
        if (kind == "image")
            return "image"
        return "cube"
    }

    Loader
    {
        id: loader
        x: entry.inset
        y: Style.s2
        width: entry.contentWidth
        active: !entry.hidden
        sourceComponent:
        {
            switch (entry.kindText)
            {
                case "user": return userComponent
                case "activity": return activityComponent
                case "error": return errorComponent
                case "notice": return noticeComponent
                default: return assistantComponent
            }
        }
    }

    Component
    {
        id: actionRow

        Flow
        {
            width: parent ? parent.width : 0
            spacing: Style.s2
            visible: entry.actionList().length > 0

            Repeater
            {
                model: entry.actionList()

                AButton
                {
                    size: "small"
                    variant: index == 0 ? "primary" : "secondary"
                    text: entry.txt["act_" + modelData] || modelData
                    enabled: modelData == "settings" || modelData == "pick_file" || !assistant.busy
                    tooltip: enabled ? "" : entry.txt.busy_hint
                    onClicked: assistant.runAction(modelData)
                }
            }
        }
    }

    Component
    {
        id: detailsBox

        TechBlock
        {
            width: parent ? parent.width : 0
            text: model.details
            label: entry.txt.tech_details
        }
    }

    Component
    {
        id: userComponent

        Item
        {
            width: entry.contentWidth
            height: bubble.height

            Text
            {
                id: measure
                visible: false
                text: model.text
                textFormat: Text.StyledText
                font: Style.reading
            }

            Rectangle
            {
                id: bubble
                anchors.right: parent.right
                width: Math.min(Math.round(entry.contentWidth * 0.86),
                                Math.max(measure.implicitWidth + Style.px(2), files.implicitWidth, modePill.visible ? modePill.width : 0)
                                + 2 * Style.s3)
                height: userColumn.height + 2 * Style.s2 + Style.px(2)
                radius: Style.radiusLarge
                color: Style.userBubble

                Column
                {
                    id: userColumn
                    x: Style.s3
                    y: Style.s2 + Style.px(1)
                    width: parent.width - 2 * Style.s3
                    spacing: Style.s2

                    TextEdit
                    {
                        width: parent.width
                        visible: model.text != ""
                        text: model.text
                        textFormat: TextEdit.RichText
                        readOnly: true
                        selectByMouse: true
                        wrapMode: TextEdit.Wrap
                        font: Style.reading
                        color: Style.text
                        selectionColor: Style.accent
                    }

                    Column
                    {
                        id: files
                        width: parent.width
                        spacing: Style.s1
                        visible: entry.metaText != ""

                        Repeater
                        {
                            model: entry.metaText != "" ? entry.metaText.split("\n") : []

                            Row
                            {
                                property var parts: modelData.split("|")
                                spacing: Style.s2

                                Icon
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: entry.fileIcon(parent.parts[0])
                                    size: Style.iconSmall
                                    color: Style.accent
                                }

                                Text
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: parent.parts.length > 1 ? parent.parts[1] : modelData
                                    font: Style.small
                                    color: Style.textSecondary
                                    elide: Text.ElideMiddle
                                    width: Math.min(implicitWidth, userColumn.width - Style.iconSmall - Style.s2)
                                }
                            }
                        }
                    }

                    Pill
                    {
                        id: modePill
                        visible: model.summary != ""
                        tone: "accent"
                        text: entry.txt.mode_label + ": " + model.summary
                    }
                }
            }
        }
    }

    Component
    {
        id: assistantComponent

        AnswerView
        {
            width: entry.contentWidth
            blocks: model.blocks
            plain: model.plain
            collapsible: model.collapsible
            textColor: model.summary == "intermediate" ? Style.textSecondary : Style.text
        }
    }

    Component
    {
        id: activityComponent

        ActivityCard
        {
            width: entry.contentWidth
            phase: model.phase
            title: model.title
            progress: model.progress
            percent: model.percent
            indeterminate: model.indeterminate
            stages: model.stages
            stageCount: model.stageCount
            summary: model.summary
            metrics: model.metrics
            changes: model.changes
            decisions: model.decisions
            exports: model.exports
            impact: model.impact
            actions: model.actions
            serious: model.serious
            liveText: active ? assistant.liveStatus : ""
        }
    }

    Component
    {
        id: errorComponent

        Rectangle
        {
            width: entry.contentWidth
            height: errorColumn.height + 2 * Style.s4
            radius: Style.radiusLarge
            color: Style.dangerSoft

            Icon
            {
                id: errorIcon
                x: Style.s4
                y: Style.s4 + Style.px(1)
                name: "alert"
                color: Style.danger
            }

            Column
            {
                id: errorColumn
                anchors.left: errorIcon.right
                anchors.leftMargin: Style.s3
                anchors.right: parent.right
                anchors.rightMargin: Style.s4
                y: Style.s4
                spacing: Style.s2

                Text
                {
                    width: parent.width
                    text: model.title
                    font: Style.bodyStrong
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                TextEdit
                {
                    width: parent.width
                    text: model.text
                    textFormat: TextEdit.RichText
                    readOnly: true
                    selectByMouse: true
                    font: Style.body
                    color: Style.text
                    wrapMode: TextEdit.Wrap
                    selectionColor: Style.accent
                }

                Text
                {
                    width: parent.width
                    visible: model.impact != ""
                    text: model.impact
                    font: Style.small
                    color: Style.textSecondary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Loader
                {
                    width: parent.width
                    sourceComponent: actionRow
                    active: entry.actionsText != ""
                    visible: active
                }

                AButton
                {
                    visible: model.details != ""
                    size: "small"
                    variant: "link"
                    iconName: entry.expanded ? "chevron-down" : "chevron-right"
                    text: entry.expanded ? entry.txt.hide_details : entry.txt.details
                    onClicked: entry.expanded = !entry.expanded
                }

                Loader
                {
                    width: parent.width
                    sourceComponent: detailsBox
                    active: entry.expanded
                    visible: active
                }
            }
        }
    }

    Component
    {
        id: noticeComponent

        Column
        {
            width: entry.contentWidth
            spacing: Style.s2

            Row
            {
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: Style.s2

                Icon
                {
                    anchors.verticalCenter: parent.verticalCenter
                    name: "info"
                    size: Style.iconSmall
                    color: Style.textMuted
                }

                Text
                {
                    anchors.verticalCenter: parent.verticalCenter
                    width: Math.min(implicitWidth, entry.contentWidth - Style.iconSmall - Style.s2)
                    text: model.text
                    font: Style.small
                    color: Style.textSecondary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }

            Loader
            {
                anchors.horizontalCenter: parent.horizontalCenter
                width: item ? item.childrenRect.width : 0
                sourceComponent: actionRow
                active: entry.actionsText != ""
                visible: active
            }
        }
    }
}
