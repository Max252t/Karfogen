import QtQuick 2.2
import "."

Item
{
    id: field
    property alias text: input.text
    property string placeholder: ""
    property bool password: false
    property bool invalid: false
    property int maximumLength: 32767
    signal accepted()
    signal cancelled()

    function selectAll()
    {
        input.selectAll()
    }

    implicitHeight: Style.controlHeight
    implicitWidth: Style.px(240)
    activeFocusOnTab: true
    onActiveFocusChanged: if (activeFocus) input.forceActiveFocus()

    Rectangle
    {
        anchors.fill: parent
        anchors.margins: -Style.focusWidth
        radius: Style.radius + Style.focusWidth
        color: "transparent"
        border.width: Style.focusWidth
        border.color: field.invalid ? Qt.rgba(0.75, 0.21, 0.17, 0.35) : Style.focusRing
        visible: input.activeFocus
    }

    Rectangle
    {
        anchors.fill: parent
        radius: Style.radius
        color: Style.surface
        border.width: Style.line
        border.color: field.invalid ? Style.danger : (input.activeFocus ? Style.accent : (hover.containsMouse ? Style.borderStrong : Style.border))
    }

    TextInput
    {
        id: input
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.s3
        anchors.rightMargin: Style.s3
        clip: true
        font: Style.body
        color: Style.text
        selectionColor: Style.accent
        selectByMouse: true
        echoMode: field.password ? TextInput.Password : TextInput.Normal
        passwordCharacter: "•"
        maximumLength: field.maximumLength
        Keys.onReturnPressed: field.accepted()
        Keys.onEnterPressed: field.accepted()
        Keys.onEscapePressed:
        {
            field.cancelled()
            event.accepted = false
        }
    }

    Text
    {
        anchors.fill: input
        verticalAlignment: Text.AlignVCenter
        visible: input.text == "" && !input.inputMethodComposing
        text: field.placeholder
        font: Style.body
        color: Style.textMuted
        elide: Text.ElideRight
    }

    MouseArea
    {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        cursorShape: Qt.IBeamCursor
    }
}
