import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Dialogs 1.1
import QtQuick.Window 2.2
import UM 1.2 as UM
import "."

Window
{
    id: dialog
    property var txt: assistant.strings
    property bool testing: false
    property string testMessage: ""
    property bool testOk: false
    readonly property var languages: ["auto", "ru", "en"]

    function open()
    {
        var s = assistant.settings
        baseUrl.text = s.base_url || ""
        modelField.text = s.model || ""
        apiKey.text = ""
        explain.checked = s.explain !== false
        autoExport.checked = s.auto_export !== false
        verifySsl.checked = s.verify_ssl !== false
        resultsDir.text = s.results_dir || ""
        var index = dialog.languages.indexOf(s.language || "auto")
        language.currentIndex = index < 0 ? 0 : index
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
            "verify_ssl": verifySsl.checked,
            "results_dir": resultsDir.text,
            "language": dialog.languages[language.currentIndex]
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

    title: txt.set_title
    modality: Qt.WindowModal
    flags: Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint
    width: Math.round(480 * Style.scale)
    height: Math.min(form.height + buttons.height + 4 * Style.margin, Math.round(680 * Style.scale))
    minimumWidth: Math.round(380 * Style.scale)
    minimumHeight: Math.round(320 * Style.scale)
    color: Style.background

    Connections
    {
        target: assistant
        onTestFinished:
        {
            dialog.testing = false
            dialog.testOk = ok
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
        Keys.onEscapePressed: dialog.visible = false

        ScrollView
        {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: buttons.top
            anchors.bottomMargin: Style.margin
            style: UM.Theme.styles.scrollview

            Item
            {
                width: dialog.width - Style.margin
                height: form.height + 2 * Style.margin

                Column
                {
                    id: form
                    x: Style.margin
                    y: Style.margin
                    width: parent.width - 2 * Style.margin
                    spacing: Style.narrow

                    Text
                    {
                        width: parent.width
                        text: txt.set_hint
                        font: Style.font
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Text { text: txt.set_base_url; font: Style.fontBold; color: Style.text }

                    TextField
                    {
                        id: baseUrl
                        property string unit: ""
                        width: parent.width
                        height: Style.controlHeight
                        placeholderText: "https://api.openai.com/v1"
                        style: UM.Theme.styles.text_field
                    }

                    Text { text: txt.set_model; font: Style.fontBold; color: Style.text }

                    TextField
                    {
                        id: modelField
                        property string unit: ""
                        width: parent.width
                        height: Style.controlHeight
                        placeholderText: "gpt-4.1"
                        style: UM.Theme.styles.text_field
                    }

                    Text { text: txt.set_key; font: Style.fontBold; color: Style.text }

                    TextField
                    {
                        id: apiKey
                        property string unit: ""
                        width: parent.width
                        height: Style.controlHeight
                        echoMode: TextInput.Password
                        placeholderText: assistant.settings.api_key_set ? "••••••••" : "sk-…"
                        style: UM.Theme.styles.text_field
                    }

                    Text
                    {
                        width: parent.width
                        text: assistant.settings.api_key_set ? txt.set_key_saved.replace("%s", assistant.settings.api_key_mask) : txt.set_key_hint
                        font: Style.fontSmall
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Row
                    {
                        spacing: Style.narrow

                        AButton
                        {
                            text: dialog.testing ? txt.set_testing : txt.set_test
                            iconName: "connected"
                            enabled: !dialog.testing
                            onClicked:
                            {
                                dialog.testing = true
                                dialog.testMessage = ""
                                assistant.testConnection(dialog.values())
                            }
                        }

                        Spinner
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: dialog.testing
                        }
                    }

                    Rectangle
                    {
                        width: parent.width
                        visible: dialog.testMessage != ""
                        height: visible ? testText.height + 2 * Style.narrow : 0
                        radius: Style.radius
                        color: dialog.testOk ? Style.primaryTint : Style.dangerTint

                        Text
                        {
                            id: testText
                            x: Style.narrow
                            y: Style.narrow
                            width: parent.width - 2 * Style.narrow
                            text: dialog.testMessage
                            font: Style.font
                            color: Style.text
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }

                    Item { width: 1; height: Style.narrow }

                    Text { text: txt.set_behavior; font: Style.fontHeading; color: Style.text }

                    CheckRow { id: explain; text: txt.set_explain }
                    CheckRow { id: autoExport; text: txt.set_auto_export }
                    CheckRow { id: verifySsl; text: txt.set_verify_ssl }

                    Text { text: txt.set_language; font: Style.fontBold; color: Style.text }

                    ComboBox
                    {
                        id: language
                        width: Math.round(parent.width * 0.6)
                        model: [txt.set_lang_auto, "Русский", "English"]
                        style: UM.Theme.styles.combobox
                    }

                    Text { text: txt.set_results; font: Style.fontBold; color: Style.text }

                    Item
                    {
                        width: parent.width
                        height: Style.controlHeight

                        TextField
                        {
                            id: resultsDir
                            property string unit: ""
                            anchors.left: parent.left
                            anchors.right: browse.left
                            anchors.rightMargin: Style.narrow
                            height: Style.controlHeight
                            style: UM.Theme.styles.text_field
                        }

                        AButton
                        {
                            id: browse
                            anchors.right: parent.right
                            text: txt.set_browse
                            onClicked: folderDialog.open()
                        }
                    }

                    Text
                    {
                        width: parent.width
                        text: txt.set_results_hint
                        font: Style.fontSmall
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }
        }

        Row
        {
            id: buttons
            anchors.right: parent.right
            anchors.rightMargin: Style.margin
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.margin
            spacing: Style.narrow

            AButton
            {
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
