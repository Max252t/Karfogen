import QtQuick 2.2
import QtQuick.Controls 1.1
import "."

Item
{
    id: page
    property var txt: assistant.strings
    property string pendingId: ""
    property string pendingName: ""
    readonly property int columnX: Math.round((width - columnWidth) / 2)
    readonly property int columnWidth: Math.min(width - 2 * Style.s3, Style.readableWidth)

    ConfirmDialog
    {
        id: newDialog
        title: txt.proj_new_title
        message: txt.proj_new_text
        confirmText: txt.create
        checkText: txt.proj_new_clear
        checkHint: txt.proj_new_clear_hint
        checked: true
        onConfirmed: assistant.createProject(checked)
    }

    ConfirmDialog
    {
        id: deleteDialog
        title: txt.proj_delete_title
        message: txt.proj_delete_text.replace("%s", page.pendingName)
        confirmText: txt.delete
        danger: true
        onConfirmed: assistant.deleteProject(page.pendingId)
    }

    RenameDialog
    {
        id: renameDialog
        onAccepted: assistant.renameProject(page.pendingId, name)
    }

    Column
    {
        id: top
        width: Math.min(parent.width - 2 * Style.s3, Style.readableWidth)
        x: Math.round((parent.width - width) / 2)
        y: Style.s3
        spacing: Style.s2

        Item
        {
            width: parent.width
            height: newButton.height

            Text
            {
                anchors.left: parent.left
                anchors.right: newButton.left
                anchors.rightMargin: Style.s3
                anchors.verticalCenter: parent.verticalCenter
                text: txt.proj_title
                font: Style.headline
                color: Style.text
                elide: Text.ElideRight
            }

            AButton
            {
                id: newButton
                anchors.right: parent.right
                variant: "primary"
                iconName: "plus"
                text: txt.proj_new
                enabled: !assistant.busy
                tooltip: enabled ? "" : txt.proj_busy
                onClicked: newDialog.ask()
            }
        }

        Text
        {
            width: parent.width
            text: txt.proj_hint
            font: Style.small
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Rectangle
        {
            width: parent.width
            visible: assistant.busy
            height: visible ? busyRow.height + 2 * Style.s2 : 0
            radius: Style.radius
            color: Style.warningSoft

            Row
            {
                id: busyRow
                x: Style.s3
                y: Style.s2
                width: parent.width - 2 * Style.s3
                spacing: Style.s2

                Icon
                {
                    name: "info"
                    size: Style.iconSmall
                    color: Style.warning
                }

                Text
                {
                    width: parent.width - Style.iconSmall - Style.s2
                    text: txt.proj_busy
                    font: Style.small
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }
            }
        }
    }

    Text
    {
        anchors.top: top.bottom
        anchors.topMargin: Style.s6
        x: top.x
        width: top.width
        visible: assistant.projectModel.count == 0
        text: txt.proj_empty
        font: Style.body
        color: Style.textSecondary
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        horizontalAlignment: Text.AlignHCenter
    }

    ScrollView
    {
        anchors.top: top.bottom
        anchors.topMargin: Style.s3
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        style: Style.scrollStyle
        horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff
        visible: assistant.projectModel.count > 0

        ListView
        {
            id: list
            model: assistant.projectModel
            spacing: Style.px(2)
            bottomMargin: Style.s3
            boundsBehavior: Flickable.StopAtBounds

            delegate: Item
            {
                width: list.width
                height: row.height

                Rectangle
                {
                    id: row
                    property bool locked: assistant.busy && !model.current
                    property bool hot: rowMouse.containsMouse || renameButton.hovered || deleteButton.hovered
                    x: page.columnX
                    width: page.columnWidth
                    height: Math.max(info.height, Style.controlHeight) + 2 * Style.s3
                    radius: Style.radius
                    color: model.current ? Style.accentSoft : (row.hot ? Style.surface : "transparent")
                    activeFocusOnTab: true
                    Keys.onReturnPressed: if (!row.locked) assistant.openProject(model.id)
                    Keys.onSpacePressed: if (!row.locked) assistant.openProject(model.id)
                    border.width: activeFocus ? Style.focusWidth : 0
                    border.color: Style.focusRing

                    MouseArea
                    {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: row.locked ? Qt.ForbiddenCursor : Qt.PointingHandCursor
                        onClicked:
                        {
                            if (model.current)
                                assistant.showTab("chat")
                            else if (!row.locked)
                                assistant.openProject(model.id)
                        }
                    }

                    HoverTip
                    {
                        area: rowMouse
                        text: row.locked ? txt.proj_busy : model.name
                    }

                    Rectangle
                    {
                        id: badge
                        x: Style.s3
                        anchors.verticalCenter: parent.verticalCenter
                        width: Style.px(32)
                        height: width
                        radius: Style.radius
                        color: model.current ? Style.surface : Style.surfaceAlt

                        Icon
                        {
                            anchors.centerIn: parent
                            name: "folder"
                            color: model.current ? Style.accent : Style.textSecondary
                        }
                    }

                    Column
                    {
                        id: info
                        anchors.left: badge.right
                        anchors.leftMargin: Style.s3
                        anchors.right: actions.left
                        anchors.rightMargin: Style.s2
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Style.px(2)

                        Row
                        {
                            width: parent.width
                            spacing: Style.s2

                            Text
                            {
                                anchors.verticalCenter: parent.verticalCenter
                                width: Math.min(implicitWidth, parent.width - (currentPill.visible ? currentPill.width + Style.s2 : 0))
                                text: model.name
                                font: Style.bodyStrong
                                color: row.locked ? Style.textMuted : Style.text
                                elide: Text.ElideRight
                            }

                            Pill
                            {
                                id: currentPill
                                anchors.verticalCenter: parent.verticalCenter
                                visible: model.current
                                tone: "accent"
                                text: txt.proj_current_badge
                            }
                        }

                        Text
                        {
                            width: parent.width
                            text: model.updated + "  ·  " + txt.messages_count.replace("%d", model.messages)
                            font: Style.small
                            color: Style.textSecondary
                            elide: Text.ElideRight
                        }
                    }

                    Row
                    {
                        id: actions
                        anchors.right: parent.right
                        anchors.rightMargin: Style.s2
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Style.px(2)
                        opacity: row.hot || row.activeFocus || renameButton.activeFocus || deleteButton.activeFocus ? 1 : 0.55

                        IconButton
                        {
                            id: renameButton
                            iconName: "pencil"
                            tooltip: txt.rename
                            onClicked:
                            {
                                page.pendingId = model.id
                                renameDialog.ask(model.name)
                            }
                        }

                        IconButton
                        {
                            id: deleteButton
                            iconName: "trash"
                            tone: "danger"
                            tooltip: enabled ? txt.delete : txt.proj_busy
                            enabled: !(assistant.busy && model.current)
                            onClicked:
                            {
                                page.pendingId = model.id
                                page.pendingName = model.name
                                deleteDialog.ask()
                            }
                        }
                    }
                }
            }
        }
    }
}
