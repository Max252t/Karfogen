pragma Singleton
import QtQuick 2.2
import UM 1.2 as UM

QtObject
{
    readonly property real scale: screenScaleFactor

    readonly property color background: UM.Theme.getColor("sidebar")
    readonly property color panel: UM.Theme.getColor("secondary")
    readonly property color lining: UM.Theme.getColor("lining")
    readonly property color hairline: UM.Theme.getColor("monitor_lining_light")
    readonly property color text: UM.Theme.getColor("text")
    readonly property color textSecondary: UM.Theme.getColor("text_medium")
    readonly property color textMuted: UM.Theme.getColor("text_inactive")
    readonly property color primary: UM.Theme.getColor("primary")
    readonly property color primaryHover: UM.Theme.getColor("primary_hover")
    readonly property color primaryText: UM.Theme.getColor("primary_text")
    readonly property color primaryTint: Qt.rgba(primary.r, primary.g, primary.b, 0.09)
    readonly property color danger: UM.Theme.getColor("status_stopped")
    readonly property color dangerTint: Qt.rgba(danger.r, danger.g, danger.b, 0.08)
    readonly property color warning: UM.Theme.getColor("setting_validation_warning_background")
    readonly property color warningTint: Qt.rgba(warning.r, warning.g, warning.b, 0.10)
    readonly property color success: UM.Theme.getColor("status_ready")
    readonly property color progressTrack: UM.Theme.getColor("progressbar_background")
    readonly property color progressFill: UM.Theme.getColor("primary")
    readonly property color field: UM.Theme.getColor("setting_control")
    readonly property color fieldBorder: UM.Theme.getColor("setting_control_border")
    readonly property color fieldFocus: UM.Theme.getColor("setting_control_border_highlight")
    readonly property color toastBackground: UM.Theme.getColor("sidebar_header_bar")
    readonly property color toastText: UM.Theme.getColor("sidebar_header_text_active")

    readonly property int margin: UM.Theme.getSize("default_margin").width
    readonly property int narrow: UM.Theme.getSize("narrow_margin").width
    readonly property int wide: UM.Theme.getSize("wide_margin").width
    readonly property int lineWidth: Math.max(1, UM.Theme.getSize("default_lining").width)
    readonly property int radius: Math.round(4 * scale)
    readonly property int controlHeight: UM.Theme.getSize("setting_control").height
    readonly property int icon: UM.Theme.getSize("small_button_icon").width
    readonly property int smallIcon: Math.round(UM.Theme.getSize("small_button_icon").width * 0.75)

    readonly property font font: UM.Theme.getFont("default")
    readonly property font fontBold: UM.Theme.getFont("default_bold")
    readonly property font fontHeading: UM.Theme.getFont("medium_bold")
    readonly property font fontSmall: UM.Theme.getFont("very_small")
}
