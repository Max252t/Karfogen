import QtQuick 2.2
import QtQuick.Controls 1.1
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

    title: txt.window_title + " — " + assistant.projectName
    flags: Qt.Window
    modality: Qt.NonModal
    minimumWidth: Style.px(380)
    minimumHeight: Style.px(460)
    width: Style.px(420)
    height: Style.px(780)
    color: Style.window

    onVisibleChanged: if (visible) assistant.windowShown()

    Connections
    {
        target: assistant
        onShowTab: base.showTab(name)
        onNotify: toast.show(message, kind)
        onOpenSettingsRequested: settingsDialog.open()
        onPickFileRequested:
        {
            base.showTab("chat")
            chatPage.pickFile()
        }
    }

    Item
    {
        id: chrome
        anchors.fill: parent

        HeaderBar
        {
            id: header
            anchors.top: parent.top
            width: parent.width
            onSettingsClicked: settingsDialog.open()
            onProjectsClicked: base.showTab("projects")
        }

        TabBar
        {
            id: tabs
            anchors.top: header.bottom
            width: parent.width
            current: base.currentTab
            items: [{"name": "chat", "label": base.txt.tab_chat, "badge": 0},
                    {"name": "result", "label": base.txt.tab_result, "badge": assistant.changeModel.count},
                    {"name": "projects", "label": base.txt.tab_projects, "badge": 0}]
            onSelected: base.showTab(name)
        }

        RunBar
        {
            id: runBar
            showStop: base.currentTab != "chat"
            anchors.top: tabs.bottom
            width: parent.width
        }

        Item
        {
            anchors.top: runBar.bottom
            anchors.bottom: parent.bottom
            width: parent.width

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

        Toast
        {
            id: toast
            y: parent.height - height - Style.s3
               - (base.currentTab == "chat" ? chatPage.composer.height : 0)
        }
    }

    SettingsDialog
    {
        id: settingsDialog
    }
}
