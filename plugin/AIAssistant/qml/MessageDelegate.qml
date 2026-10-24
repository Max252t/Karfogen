import QtQuick 2.2
import UM 1.2 as UM
import "."

Item
{
    id: entry
    property var txt: assistant.strings
    property bool expanded: false
    property string metaText: model.meta
    property string actionsText: model.actions
    property int contentWidth: width - 2 * Style.margin
    property int maxBubble: Math.round(contentWidth * 0.85)

    width: ListView.view ? ListView.view.width : 0
    height: loader.height + Style.narrow

    function actionList()
    {
        return entry.actionsText ? entry.actionsText.split(",") : []
    }

    function kindIcon(kind)
    {
        if (kind == "image")
            return "view_normal"
        if (kind == "scene")
            return "view_3d"
        return "load"
    }

    Loader
    {
        id: loader
        x: Style.margin
        width: entry.contentWidth
        sourceComponent:
        {
            switch (model.kind)
            {
                case "user": return userComponent
                case "tool": return toolComponent
                case "error": return errorComponent
                case "notice": return noticeComponent
                case "decision": return decisionComponent
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
            spacing: Style.narrow
            visible: entry.actionList().length > 0

            Repeater
            {
                model: entry.actionList()

                AButton
                {
                    compact: true
                    variant: index == 0 ? "primary" : "secondary"
                    text: entry.txt["act_" + modelData] || modelData
                    enabled: modelData == "settings" || modelData == "pick_file" || !assistant.running
                    onClicked: assistant.runAction(modelData)
                }
            }
        }
    }

    Component
    {
        id: detailsBlock

        Column
        {
            width: parent ? parent.width : 0
            spacing: Style.narrow
            visible: model.details != ""

            Text
            {
                text: entry.expanded ? entry.txt.hide_details + " ▴" : entry.txt.details + " ▾"
                font: Style.fontSmall
                color: detailsMouse.containsMouse ? Style.primaryHover : Style.primary

                MouseArea
                {
                    id: detailsMouse
                    anchors.fill: parent
                    anchors.margins: -Style.narrow
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: entry.expanded = !entry.expanded
                }
            }

            Rectangle
            {
                visible: entry.expanded
                width: parent.width
                height: visible ? detailsText.height + 2 * Style.narrow : 0
                color: Style.panel
                radius: Style.radius

                TextEdit
                {
                    id: detailsText
                    x: Style.narrow
                    y: Style.narrow
                    width: parent.width - 2 * Style.narrow
                    text: entry.expanded ? model.details : ""
                    readOnly: true
                    selectByMouse: true
                    wrapMode: TextEdit.WrapAnywhere
                    font.family: "Consolas"
                    font.pixelSize: Math.round(11 * Style.scale)
                    color: Style.textSecondary
                }
            }
        }
    }

    Component
    {
        id: userComponent

        Item
        {
            width: entry.contentWidth
            height: bubble.height

            Rectangle
            {
                id: bubble
                anchors.right: parent.right
                width: Math.min(entry.maxBubble, Math.max(userText.implicitWidth, metaFlow.implicitWidth, modeLabel.implicitWidth)
                                + 2 * Style.margin)
                height: userColumn.height + 2 * Style.narrow
                radius: Style.radius
                color: Style.primaryTint

                Column
                {
                    id: userColumn
                    x: Style.margin
                    y: Style.narrow
                    width: parent.width - 2 * Style.margin
                    spacing: Style.narrow

                    Text
                    {
                        id: userText
                        width: parent.width
                        visible: model.text != ""
                        text: model.text
                        textFormat: Text.StyledText
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        font: Style.font
                        color: Style.text
                    }

                    Flow
                    {
                        id: metaFlow
                        width: parent.width
                        spacing: Style.narrow
                        visible: model.meta != ""

                        Repeater
                        {
                            model: entry.metaText != "" ? entry.metaText.split("\n") : []

                            Row
                            {
                                spacing: Math.round(Style.narrow / 2)
                                property var parts: modelData.split("|")

                                UM.RecolorImage
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: Style.smallIcon
                                    height: Style.smallIcon
                                    sourceSize.width: width
                                    sourceSize.height: height
                                    source: UM.Theme.getIcon(entry.kindIcon(parent.parts[0]))
                                    color: Style.primary
                                }

                                Text
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: parent.parts.length > 1 ? parent.parts[1] : modelData
                                    font: Style.fontSmall
                                    color: Style.primary
                                    elide: Text.ElideMiddle
                                    width: Math.min(implicitWidth, userColumn.width - Style.smallIcon - Style.narrow)
                                }
                            }
                        }
                    }

                    Text
                    {
                        id: modeLabel
                        visible: model.summary != ""
                        text: entry.txt.mode_fixed_hint.replace("%s", model.summary)
                        font: Style.fontSmall
                        color: Style.textSecondary
                    }
                }
            }
        }
    }

    Component
    {
        id: assistantComponent

        Item
        {
            width: entry.contentWidth
            height: assistantText.height

            TextEdit
            {
                id: assistantText
                width: Math.round(entry.contentWidth * 0.95)
                text: model.text
                textFormat: TextEdit.RichText
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                font: Style.font
                color: model.summary == "intermediate" ? Style.textSecondary : Style.text
            }
        }
    }

    Component
    {
        id: toolComponent

        Rectangle
        {
            width: entry.contentWidth
            height: toolColumn.height + 2 * Style.narrow
            radius: Style.radius
            color: Style.background
            border.width: Style.lineWidth
            border.color: model.status == "error" ? Style.danger : Style.hairline

            Column
            {
                id: toolColumn
                x: Style.margin
                y: Style.narrow
                width: parent.width - 2 * Style.margin
                spacing: Math.round(Style.narrow / 2)

                Item
                {
                    width: parent.width
                    height: Math.max(statusIcon.height, titleText.height)

                    Spinner
                    {
                        id: spinnerIcon
                        anchors.verticalCenter: parent.verticalCenter
                        visible: model.status == "running"
                    }

                    UM.RecolorImage
                    {
                        id: statusIcon
                        anchors.verticalCenter: parent.verticalCenter
                        visible: model.status != "running"
                        width: Style.smallIcon
                        height: Style.smallIcon
                        sourceSize.width: width
                        sourceSize.height: height
                        source: UM.Theme.getIcon(model.status == "error" ? "warning" : "check-outline")
                        color: model.status == "error" ? Style.danger : Style.primary
                    }

                    Text
                    {
                        id: titleText
                        anchors.left: statusIcon.right
                        anchors.leftMargin: Style.narrow
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(implicitWidth, parent.width * 0.5)
                        text: model.title
                        font: Style.fontBold
                        color: Style.text
                        elide: Text.ElideRight
                    }

                    Text
                    {
                        anchors.left: titleText.right
                        anchors.leftMargin: Style.narrow
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.summary
                        font: Style.font
                        color: model.status == "error" ? Style.danger : Style.textSecondary
                        elide: Text.ElideRight
                    }
                }

                Text
                {
                    width: parent.width
                    visible: model.status == "error" && model.impact != ""
                    text: model.impact
                    font: Style.fontSmall
                    color: Style.textSecondary
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Loader
                {
                    width: parent.width
                    sourceComponent: actionRow
                    active: model.actions != ""
                }

                Loader
                {
                    width: parent.width
                    sourceComponent: detailsBlock
                }
            }
        }
    }

    Component
    {
        id: errorComponent

        Card
        {
            width: entry.contentWidth
            accent: Style.danger

            Row
            {
                width: parent.width
                spacing: Style.narrow

                UM.RecolorImage
                {
                    width: Style.icon
                    height: Style.icon
                    sourceSize.width: width
                    sourceSize.height: height
                    source: UM.Theme.getIcon("warning")
                    color: Style.danger
                }

                Text
                {
                    width: parent.width - Style.icon - Style.narrow
                    text: model.title
                    font: Style.fontBold
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }

            Text
            {
                width: parent.width
                text: model.text
                textFormat: Text.StyledText
                font: Style.font
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Text
            {
                width: parent.width
                visible: model.impact != ""
                text: model.impact
                font: Style.fontSmall
                color: Style.textSecondary
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Loader
            {
                width: parent.width
                sourceComponent: actionRow
                active: model.actions != ""
            }

            Loader
            {
                width: parent.width
                sourceComponent: detailsBlock
            }
        }
    }

    Component
    {
        id: noticeComponent

        Column
        {
            width: entry.contentWidth
            spacing: Style.narrow

            Text
            {
                width: parent.width
                text: model.text
                font: Style.font
                color: Style.textSecondary
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Loader
            {
                anchors.horizontalCenter: parent.horizontalCenter
                width: item ? item.childrenRect.width : 0
                sourceComponent: actionRow
                active: model.actions != ""
            }
        }
    }

    Component
    {
        id: decisionComponent

        Card
        {
            width: entry.contentWidth
            tinted: true

            Text
            {
                width: parent.width
                text: model.title
                font: Style.fontBold
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }

            Text
            {
                width: parent.width
                text: model.text
                textFormat: Text.StyledText
                font: Style.font
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
        }
    }
}
