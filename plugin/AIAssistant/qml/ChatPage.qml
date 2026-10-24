import QtQuick 2.2
import QtQuick.Controls 1.1
import UM 1.2 as UM
import "."

Item
{
    id: page
    property var txt: assistant.strings
    property alias composer: composer
    signal settingsRequested()

    function pickFile()
    {
        composer.pickFile()
    }

    Item
    {
        id: feed
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: composer.top

        ScrollView
        {
            id: scroll
            anchors.fill: parent
            visible: list.count > 0
            style: UM.Theme.styles.scrollview

            ListView
            {
                id: list
                property bool stick: true
                model: assistant.messageModel
                spacing: Style.narrow
                topMargin: Style.margin
                bottomMargin: Style.margin
                boundsBehavior: Flickable.StopAtBounds
                delegate: MessageDelegate { width: list.width }

                onMovementEnded: stick = (contentY + height >= contentHeight - Style.wide)
                onCountChanged: if (stick) stickTimer.restart()
                onContentHeightChanged: if (stick) stickTimer.restart()

                Timer
                {
                    id: stickTimer
                    interval: 20
                    onTriggered: list.positionViewAtEnd()
                }
            }
        }

        Flickable
        {
            anchors.fill: parent
            visible: list.count == 0
            contentHeight: welcome.height + 2 * Style.wide
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column
            {
                id: welcome
                x: Style.wide
                y: Style.wide
                width: parent.width - 2 * Style.wide
                spacing: Style.margin

                Card
                {
                    visible: !assistant.configured
                    accent: Style.warning

                    Text
                    {
                        width: parent.width
                        text: txt.setup_title
                        font: Style.fontHeading
                        color: Style.text
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Text
                    {
                        width: parent.width
                        text: txt.setup_text
                        font: Style.font
                        color: Style.text
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Column
                    {
                        width: parent.width
                        spacing: Math.round(Style.narrow / 2)

                        Repeater
                        {
                            model: ["Base URL — " + txt.set_base_url_hint, txt.set_model + " — " + txt.set_model_hint, txt.set_key + " — " + txt.set_key_hint]

                            Text
                            {
                                width: parent.width
                                text: "•  " + modelData
                                font: Style.font
                                color: Style.textSecondary
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }

                    AButton
                    {
                        variant: "primary"
                        iconName: "settings"
                        text: txt.setup_button
                        onClicked: page.settingsRequested()
                    }
                }

                Text
                {
                    width: parent.width
                    text: txt.empty_title
                    font: Style.fontHeading
                    color: Style.text
                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                }

                Repeater
                {
                    model: [txt.empty_step1, txt.empty_step2, txt.empty_step3]

                    Row
                    {
                        width: welcome.width
                        spacing: Style.margin

                        Rectangle
                        {
                            width: Math.round(Style.controlHeight * 0.9)
                            height: width
                            radius: width / 2
                            color: Style.primaryTint

                            Text
                            {
                                anchors.centerIn: parent
                                text: index + 1
                                font: Style.fontBold
                                color: Style.primary
                            }
                        }

                        Text
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            width: welcome.width - Style.controlHeight - Style.margin
                            text: modelData
                            font: Style.font
                            color: Style.text
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }
                }

                Card
                {
                    visible: assistant.sceneModel.count > 0 && !assistant.useScene
                    tinted: true

                    Text
                    {
                        width: parent.width
                        text: txt.scene_objects
                        font: Style.fontBold
                        color: Style.text
                    }

                    Repeater
                    {
                        model: assistant.sceneModel

                        Text
                        {
                            width: parent.width
                            text: model.name + "  ·  " + model.dims
                            font: Style.font
                            color: Style.textSecondary
                            elide: Text.ElideMiddle
                        }
                    }

                    AButton
                    {
                        iconName: "view_3d"
                        text: assistant.useScene ? assistant.sceneSummary : txt.scene_use
                        onClicked:
                        {
                            assistant.setUseScene(true)
                            composer.focusInput()
                        }
                    }
                }

                Text
                {
                    width: parent.width
                    text: txt.templates
                    font: Style.fontBold
                    color: Style.text

                }

                Flow
                {
                    width: parent.width
                    spacing: Style.narrow

                    Repeater
                    {
                        model: ["tpl_load", "tpl_precise", "tpl_decor", "tpl_flex", "tpl_rotating"]

                        AButton
                        {
                            compact: true
                            text: txt[modelData]
                            onClicked: composer.insertTemplate(txt[modelData + "_text"])
                        }
                    }
                }
            }
        }

        Rectangle
        {
            anchors.fill: parent
            anchors.margins: Style.narrow
            visible: dropArea.containsDrag
            color: Style.primaryTint
            radius: Style.radius
            border.width: Math.round(2 * Style.scale)
            border.color: Style.primary

            Text
            {
                anchors.centerIn: parent
                text: txt.drop_hint
                font: Style.fontHeading
                color: Style.primary
            }
        }
    }

    Composer
    {
        id: composer
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
    }

    DropArea
    {
        id: dropArea
        anchors.fill: parent
        keys: ["text/uri-list"]
        onDropped:
        {
            if (drop.hasUrls)
                assistant.addFiles(drop.urls)
            drop.accept()
        }
    }
}
