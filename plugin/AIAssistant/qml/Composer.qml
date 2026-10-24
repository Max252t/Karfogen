import QtQuick 2.2
import QtQuick.Dialogs 1.1
import "."

Item
{
    id: composer
    property var txt: assistant.strings
    property alias text: input.text
    property bool sceneOpen: false
    readonly property bool hasContext: assistant.attachmentModel.count > 0 || assistant.sceneModel.count > 0
    readonly property bool canSend: !assistant.busy && (input.text.trim() != "" || assistant.attachmentModel.count > 0
                                                          || assistant.useScene)
    readonly property bool narrow: width < Style.px(470)

    height: column.height + Style.s3

    Connections
    {
        target: assistant
        onComposerReset:
        {
            input.text = ""
            composer.sceneOpen = false
        }
    }

    function submit()
    {
        if (!composer.canSend)
            return
        if (assistant.send(input.text))
            input.text = ""
    }

    function insertTemplate(template)
    {
        var current = input.text.replace(/\s+$/, "")
        input.text = current != "" ? current + "\n\n" + template : template
        var start = current != "" ? current.length + 2 : 0
        var lineEnd = input.text.indexOf("\n", start)
        input.cursorPosition = lineEnd == -1 ? input.text.length : lineEnd
        input.forceActiveFocus()
    }

    function pickFile()
    {
        fileDialog.open()
    }

    function focusInput()
    {
        input.forceActiveFocus()
    }

    FileDialog
    {
        id: fileDialog
        title: txt.attach_title
        selectMultiple: true
        nameFilters: [txt.attach_filter]
        onAccepted: assistant.addFiles(fileDialog.fileUrls)
    }

    Column
    {
        id: column
        x: Math.max(Style.s3, Math.round((parent.width - Style.readableWidth) / 2))
        width: parent.width - 2 * x
        spacing: Style.s2

        Row
        {
            visible: assistant.busy
            width: parent.width
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
                width: parent.width - Style.iconSmall - Style.s2
                text: txt.busy_hint
                font: Style.small
                color: Style.textSecondary
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
        }

        Rectangle
        {
            id: box
            width: parent.width
            height: inner.height + 2 * Style.s2
            radius: Style.radiusLarge
            color: Style.surface
            border.width: Style.line
            border.color: input.activeFocus ? Style.accent : Style.border

            Rectangle
            {
                anchors.fill: parent
                anchors.margins: -Style.focusWidth
                radius: parent.radius + Style.focusWidth
                color: "transparent"
                border.width: Style.focusWidth
                border.color: Style.focusRing
                visible: input.activeFocus
            }

            Column
            {
                id: inner
                x: Style.s2
                y: Style.s2
                width: parent.width - 2 * Style.s2
                spacing: Style.s2

                Flow
                {
                    id: contextFlow
                    width: parent.width
                    spacing: Style.s2
                    visible: composer.hasContext

                    ContextChip
                    {
                        visible: assistant.sceneModel.count > 0
                        kind: "model"
                        removable: false
                        selected: assistant.useScene
                        expandable: assistant.sceneModel.count > 1
                        expanded: composer.sceneOpen
                        maxWidth: contextFlow.width
                        title: assistant.sceneModel.count > 1 ? txt.scene_chip_many : txt.scene_chip
                        subtitle: assistant.sceneSubtitle
                        tooltip: txt.scene_tip
                        onClicked:
                        {
                            if (assistant.sceneModel.count > 1)
                            {
                                composer.sceneOpen = !composer.sceneOpen
                                if (composer.sceneOpen && !assistant.useScene)
                                    assistant.selectWholeScene()
                            }
                            else
                                assistant.setUseScene(!assistant.useScene)
                        }
                    }

                    Repeater
                    {
                        model: assistant.attachmentModel

                        ContextChip
                        {
                            kind: model.kind
                            title: model.name
                            subtitle: model.size
                            thumbnail: model.kind == "image" ? model.url : ""
                            maxWidth: contextFlow.width
                            removeTip: txt.remove + ": " + model.name
                            onRemoved: assistant.removeAttachment(model.id)
                        }
                    }
                }

                Column
                {
                    width: parent.width
                    visible: composer.sceneOpen && assistant.sceneModel.count > 1
                    spacing: Style.s1

                    Repeater
                    {
                        model: assistant.sceneModel

                        CheckRow
                        {
                            text: model.name
                            secondary: model.dims
                            checked: model.selected && assistant.useScene
                            onToggled:
                            {
                                if (!assistant.useScene)
                                    assistant.setUseScene(true)
                                assistant.toggleSceneObject(model.id)
                            }
                        }
                    }

                    Row
                    {
                        spacing: Style.s2

                        AButton
                        {
                            size: "small"
                            variant: "link"
                            text: txt.scene_all
                            onClicked: assistant.selectWholeScene()
                        }

                        AButton
                        {
                            size: "small"
                            variant: "link"
                            visible: assistant.useScene
                            text: txt.remove
                            onClicked:
                            {
                                assistant.setUseScene(false)
                                composer.sceneOpen = false
                            }
                        }
                    }
                }

                Flickable
                {
                    id: flick
                    width: parent.width
                    height: Math.min(Math.max(input.contentHeight, Style.px(44)), Style.px(180))
                    contentWidth: width
                    contentHeight: input.contentHeight
                    clip: true
                    flickableDirection: Flickable.VerticalFlick
                    boundsBehavior: Flickable.StopAtBounds

                    function ensureVisible(rect)
                    {
                        if (contentY >= rect.y)
                            contentY = rect.y
                        else if (contentY + height <= rect.y + rect.height)
                            contentY = rect.y + rect.height - height
                    }

                    TextEdit
                    {
                        id: input
                        x: Style.s2
                        width: flick.width - 2 * Style.s2
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        font: Style.reading
                        color: Style.text
                        selectionColor: Style.accent
                        activeFocusOnTab: true
                        onCursorRectangleChanged: flick.ensureVisible(cursorRectangle)

                        Keys.onPressed:
                        {
                            if ((event.key == Qt.Key_Return || event.key == Qt.Key_Enter) && !(event.modifiers & Qt.ShiftModifier))
                            {
                                event.accepted = true
                                composer.submit()
                            }
                        }
                    }

                    Text
                    {
                        x: input.x
                        width: input.width
                        visible: input.text == ""
                        text: txt.input_placeholder
                        font: Style.reading
                        color: Style.textMuted
                        elide: Text.ElideRight
                    }

                    MouseArea
                    {
                        anchors.fill: parent
                        acceptedButtons: Qt.NoButton
                        cursorShape: Qt.IBeamCursor
                    }
                }

                Item
                {
                    width: parent.width
                    height: composer.narrow ? modeHolder.height + Style.s2 + actionRow.height : actionRow.height

                    Item
                    {
                        id: modeHolder
                        x: composer.narrow ? 0 : attachButton.width + Style.s2
                        y: composer.narrow ? 0 : Math.round((actionRow.height - height) / 2)
                        width: modeRow.width
                        height: modeRow.height

                        Row
                        {
                            id: modeRow
                            spacing: Style.s2

                            Segmented
                            {
                                current: assistant.mode
                                options: [{"value": "auto", "label": txt.mode_auto, "hint": txt.mode_auto_tip},
                                          {"value": "classic", "label": "3D", "hint": txt.mode_fixed_tip.replace("%s", "3D")},
                                          {"value": "cylindrical", "label": "5D Spiral", "hint": txt.mode_fixed_tip.replace("%s", "5D Spiral")},
                                          {"value": "cylindrical_full", "label": "5D", "hint": txt.mode_fixed_tip.replace("%s", "5D")}]
                                onSelected: assistant.setMode(value)
                            }
                        }
                    }

                    Item
                    {
                        id: actionRow
                        y: composer.narrow ? modeHolder.height + Style.s2 : 0
                        width: parent.width
                        height: Style.controlLarge

                        IconButton
                        {
                            id: attachButton
                            anchors.verticalCenter: parent.verticalCenter
                            iconName: "paperclip"
                            tooltip: txt.attach_tip
                            onClicked: fileDialog.open()
                        }

                        AButton
                        {
                            id: sendButton
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            visible: !assistant.running
                            size: "large"
                            variant: "primary"
                            iconName: "send"
                            text: txt.send
                            iconOnly: composer.width < Style.px(400)
                            enabled: composer.canSend
                            tooltip: assistant.busy ? txt.busy_hint : (iconOnly ? txt.send + " (Enter)" : "Enter")
                            onClicked: composer.submit()
                        }

                        AButton
                        {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            visible: assistant.running
                            size: "large"
                            variant: "secondary"
                            iconName: "stop"
                            text: assistant.stopping ? txt.run_stopping : txt.stop
                            enabled: !assistant.stopping
                            onClicked: assistant.stopAgent()
                        }
                    }
                }
            }
        }

        Text
        {
            width: parent.width
            visible: !composer.narrow
            text: txt.input_hint
            font: Style.caption
            color: Style.textMuted
            horizontalAlignment: Text.AlignRight
            elide: Text.ElideRight
        }
    }
}
