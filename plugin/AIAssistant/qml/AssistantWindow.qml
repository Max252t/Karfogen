import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.2
import UM 1.2 as UM
import "."

Window
{
    id: base
    property var txt: assistant.strings
    property string currentTab: assistant.initialTab

    function showTab(name)
    {
        base.currentTab = name
        if (name == "chat")
            chatPage.composer.focusInput()
    }

    function restoreGeometry()
    {
        var g = assistant.windowGeometry
        if (g.width)
        {
            base.width = g.width
            base.height = g.height
            if (g.x !== undefined)
            {
                base.x = g.x
                base.y = g.y
            }
        }
    }

    function rememberGeometry()
    {
        assistant.saveGeometry(base.x, base.y, base.width, base.height)
    }

    title: txt.window_title + " — " + assistant.projectName
    flags: Qt.Window
    modality: Qt.NonModal
    minimumWidth: Math.round(400 * Style.scale)
    minimumHeight: Math.round(460 * Style.scale)
    width: Math.round(560 * Style.scale)
    height: Math.round(760 * Style.scale)
    color: Style.background

    Component.onCompleted: restoreGeometry()
    onClosing: rememberGeometry()
    onVisibleChanged:
    {
        if (visible)
            assistant.windowShown()
        else
            rememberGeometry()
    }

    Connections
    {
        target: assistant
        onShowTab: base.showTab(name)
        onToast: toast.show(message)
        onOpenSettingsRequested: settingsDialog.open()
        onPickFileRequested:
        {
            base.showTab("chat")
            chatPage.pickFile()
        }
    }

    ColumnLayout
    {
        anchors.fill: parent
        spacing: 0

        HeaderBar
        {
            Layout.fillWidth: true
            Layout.preferredHeight: height
            onSettingsClicked: settingsDialog.open()
        }

        RunBar
        {
            Layout.fillWidth: true
            Layout.preferredHeight: height
        }

        TabBar
        {
            Layout.fillWidth: true
            Layout.preferredHeight: height
            current: base.currentTab
            items: [{"name": "chat", "label": base.txt.tab_chat, "badge": 0},
                    {"name": "result", "label": base.txt.tab_result, "badge": assistant.changeModel.count},
                    {"name": "projects", "label": base.txt.tab_projects, "badge": 0}]
            onSelected: base.showTab(name)
        }

        Item
        {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ChatPage
            {
                id: chatPage
                anchors.fill: parent
                visible: base.currentTab == "chat"
                onSettingsRequested: settingsDialog.open()
            }

            ResultPage
            {
                anchors.fill: parent
                visible: base.currentTab == "result"
            }

            ProjectsPage
            {
                anchors.fill: parent
                visible: base.currentTab == "projects"
            }
        }
    }

    Toast
    {
        id: toast
    }

    SettingsDialog
    {
        id: settingsDialog
    }
}
