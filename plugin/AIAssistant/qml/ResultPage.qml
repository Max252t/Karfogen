import QtQuick 2.2
import QtQuick.Controls 1.1
import UM 1.2 as UM
import "."

Item
{
    id: page
    property var txt: assistant.strings
    property bool historyOpen: false
    readonly property var slice: assistant.sliceInfo
    readonly property var setup: assistant.setup
    readonly property var exports: assistant.exports

    function stateTitle()
    {
        var state = assistant.taskState
        if (state == "running")
            return txt.res_running
        if (state == "done")
            return txt.res_done
        if (state == "error")
            return txt.res_error
        return txt.res_idle
    }

    function sliceTitle()
    {
        var state = page.slice.state
        if (state == "slicing")
            return txt.res_slice_running
        if (state == "done")
            return txt.res_slice_done
        if (state == "error")
            return txt.res_slice_error
        return txt.res_slice_idle
    }

    ConfirmDialog
    {
        id: resetDialog
        title: txt.res_reset_title
        message: txt.res_reset_text
        confirmText: txt.act_reset
        danger: true
        onConfirmed: assistant.resetChanges()
    }

    ScrollView
    {
        id: scroll
        anchors.fill: parent
        style: UM.Theme.styles.scrollview

        Item
        {
            width: scroll.viewport.width
            height: content.height + 2 * Style.margin

            Column
            {
                id: content
                x: Style.margin
                y: Style.margin
                width: parent.width - 2 * Style.margin
                spacing: Style.margin

                Card
                {
                    accent: assistant.taskState == "error" ? Style.danger : (assistant.taskState == "done" ? Style.success : Style.primary)

                    Row
                    {
                        width: parent.width
                        spacing: Style.narrow

                        Spinner
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: assistant.running
                        }

                        Text
                        {
                            width: parent.width - Style.icon
                            text: page.stateTitle()
                            font: Style.fontHeading
                            color: Style.text
                            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                        }
                    }

                    Text
                    {
                        width: parent.width
                        visible: assistant.running
                        text: assistant.statusText
                        font: Style.font
                        color: Style.primary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    KeyValue { key: txt.res_mode; value: page.setup.mode }
                    KeyValue { key: txt.res_material; value: page.setup.material }
                    KeyValue { key: txt.res_quality; value: page.setup.quality }
                }

                Card
                {
                    SectionTitle { text: txt.res_slicing }

                    Item
                    {
                        width: parent.width
                        height: sliceStateText.height

                        Text
                        {
                            id: sliceStateText
                            text: page.sliceTitle()
                            font: Style.font
                            color: page.slice.state == "error" ? Style.danger : Style.textSecondary
                        }

                        Text
                        {
                            anchors.right: parent.right
                            visible: page.slice.state == "slicing" || page.slice.state == "done"
                            text: Math.round(page.slice.progress * 100) + " %"
                            font: Style.fontBold
                            color: Style.text
                        }
                    }

                    Rectangle
                    {
                        width: parent.width
                        height: Math.round(6 * Style.scale)
                        radius: height / 2
                        color: Style.progressTrack

                        Rectangle
                        {
                            width: parent.width * page.slice.progress
                            height: parent.height
                            radius: parent.radius
                            color: page.slice.state == "error" ? Style.danger : Style.progressFill
                        }
                    }

                    Row
                    {
                        width: parent.width
                        visible: page.slice.time != ""

                        Repeater
                        {
                            model: [[txt.res_time, page.slice.time], [txt.res_length, page.slice.length], [txt.res_weight, page.slice.weight]]

                            Column
                            {
                                width: content.width / 3 - Style.margin

                                Text
                                {
                                    width: parent.width
                                    text: modelData[0]
                                    font: Style.fontSmall
                                    color: Style.textSecondary
                                    wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                                }

                                Text
                                {
                                    width: parent.width
                                    text: modelData[1] || "—"
                                    font: Style.fontHeading
                                    color: Style.text
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                Card
                {
                    SectionTitle { text: txt.res_export }

                    Text
                    {
                        width: parent.width
                        visible: page.slice.state != "done"
                        text: txt.res_export_hint
                        font: Style.fontSmall
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Flow
                    {
                        width: parent.width
                        spacing: Style.narrow

                        AButton
                        {
                            variant: "primary"
                            iconName: "check-outline"
                            text: txt.res_save_gcode
                            enabled: page.slice.state == "done" && page.exports.busy == "" && !assistant.running
                            onClicked: assistant.exportFile("gcode")
                        }

                        AButton
                        {
                            text: txt.res_save_3mf
                            enabled: page.exports.busy == "" && !assistant.running
                            onClicked: assistant.exportFile("3mf")
                        }

                        AButton
                        {
                            variant: "ghost"
                            iconName: "load"
                            text: txt.res_open_folder
                            onClicked: assistant.openResultsFolder()
                        }

                        AButton
                        {
                            variant: "ghost"
                            text: txt.res_screenshot
                            onClicked: assistant.saveScreenshot()
                        }
                    }

                    Repeater
                    {
                        model: [page.exports.gcode, page.exports["3mf"]]

                        TextEdit
                        {
                            width: content.width - 2 * Style.margin
                            visible: modelData != ""
                            text: txt.res_saved_to.replace("%s", modelData)
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.WrapAnywhere
                            font: Style.fontSmall
                            color: Style.textSecondary
                        }
                    }
                }

                Card
                {
                    visible: assistant.decisionModel.count > 0

                    SectionTitle { text: txt.res_decisions }

                    Repeater
                    {
                        model: assistant.decisionModel

                        KeyValue
                        {
                            key: model.label
                            value: model.value
                            secondary: model.reason
                        }
                    }
                }

                Card
                {
                    SectionTitle
                    {
                        text: txt.res_changes
                        badge: assistant.changeModel.count > 0 ? String(assistant.changeModel.count) : ""
                    }

                    Text
                    {
                        width: parent.width
                        visible: assistant.changeModel.count == 0
                        text: txt.res_no_changes
                        font: Style.font
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Repeater
                    {
                        model: assistant.changeModel

                        KeyValue
                        {
                            key: model.label
                            value: model.old != "" ? txt.res_old_new.replace("%s", model.old).replace("%s", model.value) : model.value
                            secondary: model.key != model.label ? model.key : ""
                        }
                    }

                    Text
                    {
                        width: parent.width
                        visible: page.setup.userChanges > 0
                        text: txt.res_user_changes.replace("%d", page.setup.userChanges)
                        font: Style.fontSmall
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    AButton
                    {
                        visible: page.setup.userChanges > 0 || assistant.changeModel.count > 0
                        variant: "danger"
                        iconName: "reset"
                        text: txt.res_reset
                        enabled: !assistant.running && page.exports.busy == ""
                        onClicked: resetDialog.ask()
                    }
                }

                Card
                {
                    visible: assistant.toolCount > 0

                    Item
                    {
                        width: parent.width
                        height: historyTitle.height

                        SectionTitle
                        {
                            id: historyTitle
                            text: txt.history_actions.replace("%d", assistant.toolCount) + (page.historyOpen ? "  ▴" : "  ▾")
                        }

                        MouseArea
                        {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: page.historyOpen = !page.historyOpen
                        }
                    }

                    Column
                    {
                        width: parent.width
                        visible: page.historyOpen
                        spacing: Math.round(Style.narrow / 2)

                        Repeater
                        {
                            model: page.historyOpen ? assistant.messageModel : null

                            Item
                            {
                                width: parent.width
                                visible: model.kind == "tool"
                                height: visible ? historyRow.height : 0

                                Row
                                {
                                    id: historyRow
                                    width: parent.width
                                    spacing: Style.narrow

                                    UM.RecolorImage
                                    {
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: Style.smallIcon
                                        height: Style.smallIcon
                                        sourceSize.width: width
                                        sourceSize.height: height
                                        source: UM.Theme.getIcon(model.status == "error" ? "warning" : (model.status == "running" ? "rotate" : "check-outline"))
                                        color: model.status == "error" ? Style.danger : Style.primary
                                    }

                                    Text
                                    {
                                        width: parent.width - Style.smallIcon - Style.narrow
                                        text: model.title + " — " + model.summary
                                        font: Style.fontSmall
                                        color: Style.text
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
