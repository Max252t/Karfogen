import QtQuick 2.2
import QtQuick.Controls 1.1
import "."

Item
{
    id: page
    property var txt: assistant.strings
    readonly property var slice: assistant.sliceInfo
    readonly property var setup: assistant.setup
    readonly property var exports: assistant.exports
    readonly property bool idle: !assistant.busy
    readonly property bool canExportGcode: slice.ready && idle

    function status()
    {
        if (page.slice.state == "slicing")
            return {"tone": "accent", "icon": "", "title": txt.res_slicing_now, "hint": ""}
        if (page.slice.state == "error")
            return {"tone": "danger", "icon": "alert", "title": txt.res_slice_error, "hint": txt.res_failed_hint}
        if (page.slice.ready)
            return {"tone": "success", "icon": "check-circle", "title": txt.res_ready, "hint": ""}
        if (page.slice.historical)
            return {"tone": "warning", "icon": "warning", "title": txt.res_stale, "hint": txt.res_stale_hint}
        return {"tone": "neutral", "icon": "info", "title": txt.res_not_sliced, "hint": txt.res_not_sliced_hint}
    }

    function modeNote()
    {
        if (page.setup.mode == "")
            return ""
        if (assistant.requestedMode != "")
            return txt.res_mode_by_user
        if (assistant.appliedMode != "")
            return txt.res_mode_by_agent
        return ""
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
        style: Style.scrollStyle
        horizontalScrollBarPolicy: Qt.ScrollBarAlwaysOff

        Item
        {
            width: scroll.viewport.width
            height: content.height + 2 * Style.s3

            Column
            {
                id: content
                width: Math.min(parent.width - 2 * Style.s3, Style.readableWidth)
                x: Math.round((parent.width - width) / 2)
                y: Style.s3
                spacing: Style.s3

                Card
                {
                    id: summary
                    property var info: page.status()

                    Row
                    {
                        spacing: Style.s2

                        Spinner
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            visible: page.slice.state == "slicing"
                        }

                        Pill
                        {
                            anchors.verticalCenter: parent.verticalCenter
                            tone: summary.info.tone
                            iconName: summary.info.icon
                            text: summary.info.title
                        }
                    }

                    Text
                    {
                        width: parent.width
                        visible: summary.info.hint != ""
                        text: summary.info.hint
                        font: Style.small
                        color: Style.textSecondary
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }

                    Rectangle
                    {
                        visible: page.slice.state == "slicing"
                        width: parent.width
                        height: Style.px(6)
                        radius: height / 2
                        color: Style.surfaceAlt

                        Rectangle
                        {
                            width: parent.width * page.slice.progress
                            height: parent.height
                            radius: parent.radius
                            color: Style.accent
                        }
                    }

                    Grid
                    {
                        id: metrics
                        visible: page.slice.time != "" || page.slice.weight != ""
                        width: parent.width
                        columns: width < Style.px(360) ? 1 : 3
                        spacing: Style.s2
                        opacity: page.slice.historical ? 0.75 : 1

                        Repeater
                        {
                            model: [[txt.res_time, page.slice.time], [txt.res_length, page.slice.length],
                                    [txt.res_weight, page.slice.weight]]

                            Rectangle
                            {
                                width: (metrics.width - (metrics.columns - 1) * metrics.spacing) / metrics.columns
                                height: tile.height + 2 * Style.s3
                                radius: Style.radius
                                color: Style.surfaceAlt

                                Column
                                {
                                    id: tile
                                    x: Style.s3
                                    y: Style.s3
                                    width: parent.width - 2 * Style.s3
                                    spacing: Style.px(2)

                                    Text
                                    {
                                        width: parent.width
                                        text: modelData[0]
                                        font: Style.small
                                        color: Style.textSecondary
                                        elide: Text.ElideRight
                                    }

                                    Text
                                    {
                                        width: parent.width
                                        text: modelData[1] || "—"
                                        font: Style.metric
                                        color: Style.text
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }

                    KeyValue { key: txt.res_mode; value: page.setup.mode; note: page.modeNote() }
                    KeyValue { key: txt.res_material; value: page.setup.material }
                    KeyValue { key: txt.res_quality; value: page.setup.quality }
                }

                Card
                {
                    SectionTitle
                    {
                        text: txt.res_export_section
                        hint: page.slice.ready ? "" : txt.res_gcode_needs_slice
                    }

                    Flow
                    {
                        width: parent.width
                        spacing: Style.s2

                        AButton
                        {
                            variant: "primary"
                            iconName: "download"
                            text: txt.res_save_gcode
                            enabled: page.canExportGcode && page.exports.busy == ""
                            tooltip: enabled ? "" : (page.idle ? txt.res_gcode_needs_slice : txt.busy_hint)
                            onClicked: assistant.exportFile("gcode")
                        }

                        AButton
                        {
                            variant: "secondary"
                            iconName: "download"
                            text: txt.res_save_3mf
                            enabled: page.idle && page.exports.busy == ""
                            tooltip: enabled ? "" : txt.busy_hint
                            onClicked: assistant.exportFile("3mf")
                        }

                        AButton
                        {
                            variant: "ghost"
                            iconName: "folder"
                            text: txt.res_open_folder
                            onClicked: assistant.openResultsFolder()
                        }
                    }

                    Repeater
                    {
                        model: [page.exports.gcode, page.exports["3mf"]]

                        Row
                        {
                            visible: modelData != ""
                            width: parent.width
                            spacing: Style.s2

                            Icon
                            {
                                name: "check"
                                size: Style.iconSmall
                                color: Style.success
                            }

                            TextEdit
                            {
                                width: parent.width - Style.iconSmall - Style.s2
                                text: modelData
                                readOnly: true
                                selectByMouse: true
                                wrapMode: TextEdit.WrapAnywhere
                                font: Style.small
                                color: Style.textSecondary
                                selectionColor: Style.accent
                            }
                        }
                    }
                }

                Card
                {
                    visible: assistant.decisionModel.count > 0 || assistant.changeModel.count > 0 || assistant.toolCount > 0
                    spacing: Style.s2

                    Disclosure
                    {
                        visible: assistant.decisionModel.count > 0
                        text: txt.res_decisions
                        badge: String(assistant.decisionModel.count)
                        open: true

                        Repeater
                        {
                            model: assistant.decisionModel

                            KeyValue
                            {
                                key: model.label
                                value: model.value
                                note: model.reason
                            }
                        }
                    }

                    Disclosure
                    {
                        visible: assistant.changeModel.count > 0
                        text: txt.res_changes
                        badge: String(assistant.changeModel.count)
                        open: assistant.changeModel.count <= 6

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
                    }

                    Disclosure
                    {
                        id: history
                        visible: assistant.toolCount > 0
                        text: txt.res_details
                        badge: String(assistant.toolCount)

                        Repeater
                        {
                            model: history.open ? assistant.messageModel : null

                            Row
                            {
                                visible: model.kind == "tool"
                                height: visible ? implicitHeight : 0
                                width: parent ? parent.width : 0
                                spacing: Style.s2

                                Icon
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: model.status == "error" ? "alert" : (model.status == "running" ? "spinner" : "check")
                                    size: Style.iconSmall
                                    color: model.status == "error" ? Style.danger : Style.success
                                }

                                Text
                                {
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: parent.width - Style.iconSmall - Style.s2
                                    text: model.title + (model.summary != "" ? " — " + model.summary : "")
                                    font: Style.small
                                    color: Style.textSecondary
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                Card
                {
                    visible: page.setup.userChanges > 0 || assistant.changeModel.count > 0
                    outlined: true
                    color: "transparent"

                    SectionTitle
                    {
                        text: txt.res_reset_section
                        hint: txt.res_reset_hint
                    }

                    Text
                    {
                        width: parent.width
                        visible: page.setup.userChanges > 0
                        text: txt.res_user_changes.replace("%d", page.setup.userChanges)
                        font: Style.small
                        color: Style.textSecondary
                    }

                    AButton
                    {
                        variant: "danger"
                        iconName: "rotate-ccw"
                        text: txt.res_reset
                        enabled: page.idle
                        tooltip: enabled ? "" : txt.busy_hint
                        onClicked: resetDialog.ask()
                    }
                }
            }
        }
    }
}
