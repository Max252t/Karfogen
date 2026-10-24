import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Dialogs 1.1
import UM 1.2 as UM
import "."

Rectangle
{
    id: composer
    property var txt: assistant.strings
    property alias text: input.text

    Connections
    {
        target: assistant
        onComposerReset: input.text = ""
    }
    readonly property bool canSend: !assistant.busy && (input.text.trim() != "" || assistant.attachmentModel.count > 0
                                                          || assistant.useScene)

    width: parent ? parent.width : implicitWidth
    height: column.height + 2 * Style.narrow
    color: Style.background

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

    Text
    {
        id: sendLabel
        visible: false
        text: txt.send
        font: Style.fontBold
    }

    FileDialog
    {
        id: fileDialog
        title: txt.attach_title
        selectMultiple: true
        nameFilters: [txt.attach_filter]
        onAccepted: assistant.addFiles(fileDialog.fileUrls)
    }

    Rectangle
    {
        anchors.top: parent.top
        width: parent.width
        height: Style.lineWidth
        color: Style.hairline
    }

    Column
    {
        id: column
        x: Style.margin
        y: Style.narrow
        width: parent.width - 2 * Style.margin
        spacing: Style.narrow

        Flow
        {
            width: parent.width
            spacing: Style.narrow
            visible: assistant.attachmentModel.count > 0

            Repeater
            {
                model: assistant.attachmentModel

                Rectangle
                {
                    id: chip
                    width: Math.min(chipRow.implicitWidth + 2 * Style.narrow, column.width)
                    height: Math.round(Style.controlHeight * 1.5)
                    radius: Style.radius
                    color: Style.panel
                    border.width: Style.lineWidth
                    border.color: Style.hairline

                    Row
                    {
                        id: chipRow
                        anchors.verticalCenter: parent.verticalCenter
                        x: Style.narrow
                        spacing: Style.narrow

                        Rectangle
                        {
                            width: chip.height - 2 * Style.narrow
                            height: width
                            radius: Style.radius
                            color: Style.background
                            clip: true

                            Image
                            {
                                anchors.fill: parent
                                visible: model.kind == "image"
                                source: model.kind == "image" ? model.url : ""
                                sourceSize.width: width * 2
                                sourceSize.height: height * 2
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                            }

                            Text
                            {
                                anchors.centerIn: parent
                                visible: model.kind != "image"
                                text: model.name.split(".").pop().toUpperCase()
                                font: Style.fontBold
                                color: Style.primary
                            }
                        }

                        Column
                        {
                            anchors.verticalCenter: parent.verticalCenter

                            Text
                            {
                                width: Math.min(implicitWidth, column.width * 0.45)
                                text: model.name
                                font: Style.font
                                color: Style.text
                                elide: Text.ElideMiddle
                            }

                            Text
                            {
                                text: model.size
                                font: Style.fontSmall
                                color: Style.textSecondary
                            }
                        }

                        IconButton
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            iconName: "cross1"
                            tooltip: txt.remove
                            width: Math.round(Style.controlHeight * 0.8)
                            height: width
                            onClicked: assistant.removeAttachment(model.id)
                        }
                    }
                }
            }
        }

        Column
        {
            width: parent.width
            spacing: Math.round(Style.narrow / 2)
            visible: assistant.sceneModel.count > 0

            Rectangle
            {
                id: sceneChip
                width: Math.min(sceneRow.implicitWidth + 2 * Style.narrow, parent.width)
                height: Math.round(Style.controlHeight * 0.85)
                radius: Style.radius
                color: assistant.useScene ? Style.primaryTint : (sceneMouse.containsMouse ? Style.panel : Style.background)
                border.width: Style.lineWidth
                border.color: assistant.useScene ? Style.primary : Style.lining

                Row
                {
                    id: sceneRow
                    x: Style.narrow
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: Style.narrow

                    UM.RecolorImage
                    {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Style.smallIcon
                        height: Style.smallIcon
                        sourceSize.width: width
                        sourceSize.height: height
                        source: UM.Theme.getIcon(assistant.useScene ? "check-outline" : "view_3d")
                        color: assistant.useScene ? Style.primary : Style.textSecondary
                    }

                    Text
                    {
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(implicitWidth, composer.width - 4 * Style.margin - Style.smallIcon)
                        text: assistant.useScene ? assistant.sceneSummary : txt.scene_use
                        font: Style.font
                        color: assistant.useScene ? Style.primary : Style.text
                        elide: Text.ElideRight
                    }
                }

                MouseArea
                {
                    id: sceneMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: assistant.setUseScene(!assistant.useScene)
                }
            }

            Column
            {
                x: Style.margin
                width: parent.width - Style.margin
                visible: assistant.useScene && assistant.sceneModel.count > 1
                spacing: Math.round(Style.narrow / 2)

                Repeater
                {
                    model: assistant.sceneModel

                    CheckRow
                    {
                        text: model.name
                        secondary: model.dims
                        checked: model.selected
                        onToggled: assistant.toggleSceneObject(model.id)
                    }
                }

                AButton
                {
                    compact: true
                    variant: "link"
                    text: txt.scene_all
                    onClicked: assistant.selectWholeScene()
                }
            }
        }

        Rectangle
        {
            id: inputBox
            width: parent.width
            height: Math.min(Math.max(input.contentHeight + 2 * Style.narrow, Style.controlHeight * 2),
                             Math.round(Style.controlHeight * 6))
            radius: Style.radius
            color: Style.field
            border.width: Style.lineWidth
            border.color: input.activeFocus ? Style.fieldFocus : Style.lining

            Flickable
            {
                id: flick
                anchors.fill: parent
                anchors.margins: Style.narrow
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
                    width: flick.width
                    wrapMode: TextEdit.Wrap
                    selectByMouse: true
                    font: Style.font
                    color: Style.text
                    selectionColor: Style.primary
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
            }

            Text
            {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Style.narrow
                visible: input.text == ""
                text: txt.input_placeholder
                font: Style.font
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
            height: Style.controlHeight

            IconButton
            {
                id: attachButton
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                iconName: "load"
                tooltip: txt.attach + " (STL, OBJ, 3MF, JPG, PNG)"
                onClicked: fileDialog.open()
            }

            Row
            {
                id: modeSwitch
                anchors.left: attachButton.right
                anchors.leftMargin: Style.narrow
                anchors.verticalCenter: parent.verticalCenter
                spacing: -Style.lineWidth

                Repeater
                {
                    model: [{"id": "auto", "label": txt.mode_auto, "hint": txt.mode_auto_hint},
                            {"id": "classic", "label": "3D", "hint": txt.mode_fixed_hint.replace("%s", "3D")},
                            {"id": "cylindrical", "label": "5D Spiral", "hint": txt.mode_fixed_hint.replace("%s", "5D Spiral")},
                            {"id": "cylindrical_full", "label": "5D", "hint": txt.mode_fixed_hint.replace("%s", "5D")}]

                    Rectangle
                    {
                        property bool active: assistant.mode == modelData.id
                        width: modeText.implicitWidth + 2 * Style.narrow
                        height: Math.round(Style.controlHeight * 0.85)
                        color: active ? Style.primary : (modeMouse.containsMouse ? Style.panel : Style.background)
                        border.width: Style.lineWidth
                        border.color: active ? Style.primary : Style.lining
                        z: active ? 1 : 0

                        Text
                        {
                            id: modeText
                            anchors.centerIn: parent
                            text: modelData.label
                            font: parent.active ? Style.fontBold : Style.font
                            color: parent.active ? Style.primaryText : Style.text
                        }

                        MouseArea
                        {
                            id: modeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: assistant.setMode(modelData.id)
                        }

                        UM.TooltipArea
                        {
                            anchors.fill: parent
                            acceptedButtons: Qt.NoButton
                            text: modelData.hint
                        }
                    }
                }
            }

            Text
            {
                anchors.left: modeSwitch.right
                anchors.leftMargin: Style.margin
                anchors.right: sendButton.left
                anchors.rightMargin: Style.narrow
                anchors.verticalCenter: parent.verticalCenter
                text: txt.input_hint
                font: Style.fontSmall
                color: Style.textMuted
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignRight
                visible: width > Style.wide * 4
            }

            AButton
            {
                id: sendButton
                readonly property bool roomy: parent.width > attachButton.width + modeSwitch.width + sendLabel.implicitWidth
                                              + Style.smallIcon + 5 * Style.margin
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                variant: "primary"
                text: roomy ? txt.send : ""
                iconName: "play"
                enabled: composer.canSend
                tooltip: assistant.running ? txt.busy_send : ""
                onClicked: composer.submit()
            }
        }
    }
}
