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
            style: Style.scrollStyle
            horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

            ListView
            {
                id: list
                property bool stick: true
                property int unread: 0
                model: assistant.messageModel
                topMargin: Style.s3
                bottomMargin: Style.s3
                boundsBehavior: Flickable.StopAtBounds
                cacheBuffer: Style.px(600)
                delegate: MessageDelegate { width: list.width }

                function atEnd()
                {
                    return contentY + height >= contentHeight + bottomMargin - Style.s5
                }

                onMovementEnded:
                {
                    stick = atEnd()
                    if (stick)
                        unread = 0
                }
                onCountChanged:
                {
                    if (stick)
                        stickTimer.restart()
                    else if (count > 0)
                        unread += 1
                }
                onContentHeightChanged: if (stick) stickTimer.restart()

                Timer
                {
                    id: stickTimer
                    interval: 20
                    onTriggered: list.positionViewAtEnd()
                }
            }
        }

        Rectangle
        {
            id: newMessages
            visible: list.unread > 0 && !list.stick && scroll.visible
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.bottom
            anchors.bottomMargin: Style.s2
            width: newRow.implicitWidth + 2 * Style.s3
            height: Style.controlHeight
            radius: height / 2
            color: newMouse.containsMouse ? Style.accentHover : Style.accent

            Row
            {
                id: newRow
                anchors.centerIn: parent
                spacing: Style.s1

                Icon
                {
                    anchors.verticalCenter: parent.verticalCenter
                    name: "arrow-down"
                    size: Style.iconSmall
                    color: Style.textOnAccent
                }

                Text
                {
                    anchors.verticalCenter: parent.verticalCenter
                    text: txt.new_messages
                    font: Style.smallStrong
                    color: Style.textOnAccent
                }
            }

            MouseArea
            {
                id: newMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked:
                {
                    list.stick = true
                    list.unread = 0
                    list.positionViewAtEnd()
                }
            }
        }

        Flickable
        {
            id: welcomeFlick
            anchors.fill: parent
            visible: list.count == 0
            contentHeight: Math.max(height, welcome.height + 2 * Style.s5)
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            Column
            {
                id: welcome
                width: Math.min(parent.width - 2 * Style.s5, Style.px(520))
                x: Math.round((parent.width - width) / 2)
                y: Math.max(Style.s5, Math.round((welcomeFlick.height - height) / 3))
                spacing: Style.s4

                Rectangle
                {
                    width: Style.px(44)
                    height: width
                    radius: Style.radiusLarge
                    color: Style.accentSoft

                    Icon
                    {
                        anchors.centerIn: parent
                        name: "sparkle"
                        size: Style.px(22)
                        color: Style.accent
                    }
                }

                Column
                {
                    width: parent.width
                    spacing: Style.s2

                    Text
                    {
                        width: parent.width
                        text: assistant.configured ? txt.empty_title : txt.setup_title
                        font: Style.headline
                        color: Style.text
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Text
                    {
                        width: parent.width
                        text: assistant.configured ? txt.welcome_lead : txt.setup_text
                        font: Style.body
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        lineHeight: 1.15
                    }
                }

                Column
                {
                    width: parent.width
                    spacing: Style.s3

                    Repeater
                    {
                        model: assistant.configured ? [txt.empty_step1, txt.empty_step2, txt.empty_step3]
                                                    : [txt.set_base_url + " — " + txt.set_base_url_hint,
                                                       txt.set_model + " — " + txt.set_model_hint,
                                                       txt.set_key + " — " + txt.set_key_hint]

                        Item
                        {
                            width: welcome.width
                            height: Math.max(number.height, stepText.height)

                            Rectangle
                            {
                                id: number
                                width: Style.px(24)
                                height: width
                                radius: width / 2
                                color: Style.surfaceAlt

                                Text
                                {
                                    anchors.centerIn: parent
                                    text: index + 1
                                    font: Style.smallStrong
                                    color: Style.textSecondary
                                }
                            }

                            Text
                            {
                                id: stepText
                                anchors.left: number.right
                                anchors.leftMargin: Style.s3
                                anchors.right: parent.right
                                y: Math.max(0, Math.round((number.height - Style.sizeBody * 1.35) / 2))
                                text: modelData
                                font: Style.body
                                color: Style.text
                                wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                            }
                        }
                    }
                }

                Flow
                {
                    width: parent.width
                    spacing: Style.s2

                    AButton
                    {
                        visible: !assistant.configured
                        variant: "primary"
                        iconName: "settings"
                        text: txt.setup_button
                        onClicked: page.settingsRequested()
                    }

                    AButton
                    {
                        visible: assistant.configured && assistant.sceneModel.count > 0
                        variant: assistant.useScene ? "accent" : "primary"
                        iconName: assistant.useScene ? "check" : "cube"
                        text: txt.scene_use
                        onClicked:
                        {
                            if (assistant.sceneModel.count > 1)
                                assistant.selectWholeScene()
                            else
                                assistant.setUseScene(true)
                            composer.focusInput()
                        }
                    }

                    AButton
                    {
                        visible: assistant.configured
                        variant: assistant.sceneModel.count > 0 ? "secondary" : "primary"
                        iconName: "paperclip"
                        text: txt.welcome_attach
                        onClicked: composer.pickFile()
                    }
                }

                Column
                {
                    visible: assistant.configured
                    width: parent.width
                    spacing: Style.s2

                    Text
                    {
                        text: txt.welcome_examples
                        font: Style.smallStrong
                        color: Style.textMuted
                    }

                    Flow
                    {
                        width: parent.width
                        spacing: Style.s2

                        Repeater
                        {
                            model: ["tpl_load", "tpl_precise", "tpl_decor", "tpl_flex", "tpl_rotating"]

                            AButton
                            {
                                size: "small"
                                variant: "secondary"
                                text: txt[modelData]
                                onClicked: composer.insertTemplate(txt[modelData + "_text"])
                            }
                        }
                    }
                }
            }
        }

        Rectangle
        {
            anchors.fill: parent
            anchors.margins: Style.s3
            visible: dropArea.containsDrag
            color: Style.accentSoft
            radius: Style.radiusLarge
            border.width: Style.focusWidth
            border.color: Style.accent

            Column
            {
                anchors.centerIn: parent
                spacing: Style.s2

                Icon
                {
                    anchors.horizontalCenter: parent.horizontalCenter
                    name: "paperclip"
                    size: Style.px(28)
                    color: Style.accent
                }

                Text
                {
                    text: txt.drop_hint
                    font: Style.title
                    color: Style.accent
                }
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
