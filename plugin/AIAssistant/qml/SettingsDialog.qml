import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Dialogs 1.1
import QtQuick.Window 2.2
import "."

Window
{
    id: dialog
    property var txt: assistant.strings
    property string testState: "idle"
    property string testMessage: ""
    property string language: "auto"

    function open()
    {
        var s = assistant.settings
        baseUrl.text = s.base_url || ""
        modelField.text = s.model || ""
        apiKey.text = ""
        explain.checked = s.explain !== false
        autoExport.checked = s.auto_export !== false
        liveStatus.checked = s.live_status !== false
        verifySsl.checked = s.verify_ssl !== false
        resultsDir.text = s.results_dir || ""
        dialog.language = s.language || "auto"
        dialog.testState = "idle"
        dialog.testMessage = ""
        dialog.visible = true
        dialog.requestActivate()
        baseUrl.forceActiveFocus()
    }

    function values()
    {
        return {
            "base_url": baseUrl.text,
            "model": modelField.text,
            "api_key": apiKey.text,
            "explain": explain.checked,
            "auto_export": autoExport.checked,
            "live_status": liveStatus.checked,
            "verify_ssl": verifySsl.checked,
            "results_dir": resultsDir.text,
            "language": dialog.language
        }
    }

    function save()
    {
        if (!assistant.saveSettings(dialog.values()))
            return
        dialog.visible = false
        if (assistant.configured)
            assistant.checkConnection()
    }

    function test()
    {
        dialog.testState = "running"
        dialog.testMessage = ""
        assistant.testConnection(dialog.values())
    }

    title: txt.set_title
    modality: Qt.WindowModal
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    width: Style.px(520)
    height: Math.min(form.height + footer.height + 2 * Style.s4, Style.px(720), Screen.height - Style.px(96))
    minimumWidth: Style.px(380)
    minimumHeight: Style.px(320)
    color: Style.window

    Connections
    {
        target: assistant
        onTestFinished:
        {
            dialog.testState = ok ? "ok" : "error"
            dialog.testMessage = message
        }
    }

    FileDialog
    {
        id: folderDialog
        title: txt.set_results
        selectFolder: true
        onAccepted: resultsDir.text = assistant.urlToPath(folderDialog.fileUrl)
    }

    Item
    {
        anchors.fill: parent
        focus: true
        Keys.onEscapePressed: dialog.visible = false

        ScrollView
        {
            id: scroll
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: footer.top
            style: Style.scrollStyle
            horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

            Item
            {
                width: scroll.viewport.width
                height: form.height + 2 * Style.s4

                Column
                {
                    id: form
                    x: Style.s4
                    y: Style.s4
                    width: parent.width - 2 * Style.s4
                    spacing: Style.s3

                    Column
                    {
                        width: parent.width
                        spacing: Style.s1

                        Text
                        {
                            text: txt.set_title
                            font: Style.headline
                            color: Style.text
                        }

                        Text
                        {
                            width: parent.width
                            text: txt.set_hint + " " + txt.set_required_hint
                            font: Style.small
                            color: Style.textSecondary
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }

                    Card
                    {
                        SectionTitle { text: txt.set_section_connection }

                        Column
                        {
                            width: parent.width
                            spacing: Style.s1

                            Text { text: txt.set_base_url + " *"; font: Style.bodyStrong; color: Style.text }
                            Field { id: baseUrl; width: parent.width; placeholder: "https://api.openai.com/v1"; onAccepted: dialog.save() }
                            Text { width: parent.width; text: txt.set_base_url_hint; font: Style.small; color: Style.textSecondary; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                        }

                        Column
                        {
                            width: parent.width
                            spacing: Style.s1

                            Text { text: txt.set_model + " *"; font: Style.bodyStrong; color: Style.text }
                            Field { id: modelField; width: parent.width; placeholder: "gpt-4.1"; onAccepted: dialog.save() }
                            Text { width: parent.width; text: txt.set_model_hint; font: Style.small; color: Style.textSecondary; wrapMode: Text.WrapAtWordBoundaryOrAnywhere }
                        }

                        Column
                        {
                            width: parent.width
                            spacing: Style.s1

                            Text { text: txt.set_key + " *"; font: Style.bodyStrong; color: Style.text }
                            Field
                            {
                                id: apiKey
                                width: parent.width
                                password: true
                                placeholder: assistant.settings.api_key_set ? "••••••••" : "sk-…"
                                onAccepted: dialog.save()
                            }
                            Text
                            {
                                width: parent.width
                                text: assistant.settings.api_key_set ? txt.set_key_saved.replace("%s", "••••") : txt.set_key_hint
                                font: Style.small
                                color: Style.textSecondary
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }

                        Column
                        {
                            width: parent.width
                            spacing: Style.s2

                            AButton
                            {
                                id: testButton
                                variant: "secondary"
                                iconName: "refresh"
                                text: dialog.testState == "running" ? txt.set_testing : txt.set_test
                                enabled: dialog.testState != "running"
                                onClicked: dialog.test()
                            }

                            Row
                            {
                                id: testStatus
                                width: parent.width
                                spacing: Style.s2

                                Spinner
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: dialog.testState == "running"
                                }

                                Icon
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: dialog.testState == "ok" || dialog.testState == "error"
                                    name: dialog.testState == "ok" ? "check-circle" : "alert"
                                    color: dialog.testState == "ok" ? Style.success : Style.danger
                                }

                                Text
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - Style.iconSize - Style.s2
                                    text: dialog.testState == "running" ? txt.set_testing
                                        : (dialog.testState == "idle" ? txt.set_test_idle : dialog.testMessage)
                                    font: Style.small
                                    color: dialog.testState == "ok" ? Style.success
                                         : (dialog.testState == "error" ? Style.danger : Style.textSecondary)
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }
                        }
                    }

                    Card
                    {
                        SectionTitle { text: txt.set_section_behavior }
                        CheckRow { id: explain; text: txt.set_explain }
                        CheckRow { id: autoExport; text: txt.set_auto_export }
                        CheckRow { id: liveStatus; text: txt.set_live_status; secondary: txt.set_live_status_hint }
                        CheckRow { id: verifySsl; text: txt.set_verify_ssl }
                    }

                    Card
                    {
                        SectionTitle { text: txt.set_section_results; hint: txt.set_results_hint }

                        Item
                        {
                            width: parent.width
                            height: Style.controlHeight

                            Field
                            {
                                id: resultsDir
                                anchors.left: parent.left
                                anchors.right: browse.left
                                anchors.rightMargin: Style.s2
                                height: Style.controlHeight
                                placeholder: "C:\\Users\\…\\AIAssistantResults"
                            }

                            AButton
                            {
                                id: browse
                                anchors.right: parent.right
                                variant: "secondary"
                                iconName: "folder"
                                text: txt.set_browse
                                onClicked: folderDialog.open()
                            }
                        }
                    }

                    Card
                    {
                        SectionTitle { text: txt.set_section_language; hint: txt.set_language }

                        Segmented
                        {
                            current: dialog.language
                            options: [{"value": "auto", "label": txt.set_lang_auto},
                                      {"value": "ru", "label": txt.lang_ru},
                                      {"value": "en", "label": txt.lang_en}]
                            onSelected: dialog.language = value
                        }

                        Text
                        {
                            width: parent.width
                            text: dialog.language == "auto"
                                  ? txt.set_lang_auto_hint.replace("%s", assistant.settings.language_effective_name)
                                  : txt.set_lang_fixed_hint
                            font: Style.small
                            color: Style.textSecondary
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }
                }
            }
        }

        Rectangle
        {
            id: footer
            anchors.bottom: parent.bottom
            width: parent.width
            height: Style.controlHeight + 2 * Style.s3
            color: Style.window

            Rectangle
            {
                width: parent.width
                height: Style.line
                color: Style.border
            }

            Row
            {
                anchors.right: parent.right
                anchors.rightMargin: Style.s4
                anchors.verticalCenter: parent.verticalCenter
                spacing: Style.s2

                AButton
                {
                    variant: "ghost"
                    text: txt.cancel
                    onClicked: dialog.visible = false
                }

                AButton
                {
                    variant: "primary"
                    text: txt.save
                    onClicked: dialog.save()
                }
            }
        }
    }
}
