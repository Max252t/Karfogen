import QtQuick 2.2
import QtQuick.Controls 1.1
import UM 1.2 as UM
import "."

Item
{
    id: page
    property var txt: assistant.strings
    property string pendingId: ""
    property string pendingName: ""

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
        x: Style.margin
        y: Style.margin
        width: parent.width - 2 * Style.margin
        spacing: Style.narrow

        Item
        {
            width: parent.width
            height: newButton.height

            SectionTitle
            {
                anchors.left: parent.left
                anchors.right: newButton.left
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - newButton.width - Style.margin
                text: txt.proj_title
            }

            AButton
            {
                id: newButton
                anchors.right: parent.right
                variant: "primary"
                iconName: "plus"
                text: txt.proj_new
                enabled: !assistant.running
                tooltip: assistant.running ? txt.proj_busy : ""
                onClicked: newDialog.ask()
            }
        }

        Text
        {
            width: parent.width
            text: txt.proj_hint
            font: Style.fontSmall
            color: Style.textSecondary
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }

        Rectangle
        {
            width: parent.width
            visible: assistant.running
            height: visible ? busyText.height + 2 * Style.narrow : 0
            radius: Style.radius
            color: Style.warningTint

            Text
            {
                id: busyText
                x: Style.narrow
                y: Style.narrow
                width: parent.width - 2 * Style.narrow
                text: txt.proj_busy
                font: Style.fontSmall
                color: Style.text
                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            }
        }
    }

    Text
    {
        anchors.top: top.bottom
        anchors.topMargin: Style.wide
        x: Style.margin
        width: parent.width - 2 * Style.margin
        visible: assistant.projectModel.count == 0
        text: txt.proj_empty
        font: Style.font
        color: Style.textSecondary
        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        horizontalAlignment: Text.AlignHCenter
    }

    ScrollView
    {
        anchors.top: top.bottom
        anchors.topMargin: Style.narrow
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        style: UM.Theme.styles.scrollview
        visible: assistant.projectModel.count > 0

        ListView
        {
            id: list
            model: assistant.projectModel
            spacing: Style.narrow
            bottomMargin: Style.margin
            boundsBehavior: Flickable.StopAtBounds

            delegate: Item
            {
                width: list.width
                height: row.height

                Rectangle
                {
                    id: row
                    property bool locked: assistant.running && !model.current
                    x: Style.margin
                    width: parent.width - 2 * Style.margin
                    height: Math.max(info.height, actions.height) + 2 * Style.narrow
                    radius: Style.radius
                    color: model.current ? Style.primaryTint : (rowMouse.containsMouse ? Style.panel : Style.background)
                    border.width: Style.lineWidth
                    border.color: model.current ? Style.primary : Style.hairline

                    MouseArea
                    {
                        id: rowMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: row.locked ? Qt.ArrowCursor : Qt.PointingHandCursor
                        onDoubleClicked: if (!row.locked) assistant.openProject(model.id)
                    }

                    Column
                    {
                        id: info
                        x: Style.margin
                        anchors.verticalCenter: parent.verticalCenter
                        width: parent.width - actions.width - 3 * Style.margin

                        Text
                        {
                            width: parent.width
                            text: model.name
                            font: Style.fontBold
                            color: Style.text
                            elide: Text.ElideRight
                        }

                        Text
                        {
                            width: parent.width
                            text: txt.proj_updated.replace("%s", model.updated) + "  ·  " + txt.messages_count.replace("%d", model.messages)
                                  + (model.current ? "  ·  " + txt.proj_current : "")
                            font: Style.fontSmall
                            color: Style.textSecondary
                            elide: Text.ElideRight
                        }
                    }

                    Row
                    {
                        id: actions
                        anchors.right: parent.right
                        anchors.rightMargin: Style.narrow
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: Math.round(Style.narrow / 2)

                        AButton
                        {
                            compact: true
                            text: model.current ? txt.tab_chat : txt.open
                            enabled: !row.locked
                            tooltip: row.locked ? txt.proj_busy : ""
                            onClicked: model.current ? assistant.showTab("chat") : assistant.openProject(model.id)
                        }

                        IconButton
                        {
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
                            iconName: "cross1"
                            danger: true
                            tooltip: txt.delete
                            enabled: !(assistant.running && model.current)
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
