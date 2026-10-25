pragma Singleton
import QtQuick 2.2
import QtQuick.Controls.Styles 1.1
import UM 1.2 as UM

QtObject
{
    readonly property real scale: screenScaleFactor

    function px(value)
    {
        return Math.round(value * scale)
    }

    readonly property color window: "#F5F6F8"
    readonly property color surface: "#FFFFFF"
    readonly property color surfaceAlt: "#EEF0F3"
    readonly property color surfaceHover: "#E6E9ED"
    readonly property color surfacePressed: "#DCE0E5"
    readonly property color border: "#DCE0E5"
    readonly property color borderStrong: "#C3CAD2"

    readonly property color text: "#1D2329"
    readonly property color textSecondary: "#56606B"
    readonly property color textMuted: "#7F8994"
    readonly property color textDisabled: "#9BA3AC"
    readonly property color textOnAccent: "#FFFFFF"

    readonly property color accent: UM.Theme.getColor("primary")
    readonly property color accentHover: Qt.darker(accent, 1.12)
    readonly property color accentPressed: Qt.darker(accent, 1.25)
    readonly property color accentSoft: Qt.rgba(accent.r, accent.g, accent.b, 0.10)
    readonly property color accentSoftHover: Qt.rgba(accent.r, accent.g, accent.b, 0.16)
    readonly property color focusRing: Qt.rgba(accent.r, accent.g, accent.b, 0.45)

    readonly property color success: "#1E7F45"
    readonly property color successSoft: "#E6F4EC"
    readonly property color warning: "#9A5B00"
    readonly property color warningSoft: "#FDF1DE"
    readonly property color danger: "#C0362C"
    readonly property color dangerSoft: "#FCEBEA"
    readonly property color dangerSoftHover: "#F8DCDA"
    readonly property color userBubble: Qt.rgba(accent.r, accent.g, accent.b, 0.08)
    readonly property color toast: "#2B323A"
    readonly property color toastText: "#FFFFFF"

    readonly property int s1: px(4)
    readonly property int s2: px(8)
    readonly property int s3: px(12)
    readonly property int s4: px(16)
    readonly property int s5: px(24)
    readonly property int s6: px(32)

    readonly property int radiusSmall: px(6)
    readonly property int radius: px(8)
    readonly property int radiusLarge: px(12)

    readonly property int controlHeight: px(32)
    readonly property int controlSmall: px(28)
    readonly property int controlLarge: px(36)
    readonly property int iconSize: px(16)
    readonly property int iconSmall: px(14)
    readonly property int line: Math.max(1, px(1))
    readonly property int focusWidth: Math.max(2, px(2))
    readonly property int readableWidth: px(720)

    readonly property string family: UM.Theme.getFont("default").family
    readonly property int sizeCaption: px(11)
    readonly property int sizeSmall: px(12)
    readonly property int sizeBody: px(13)
    readonly property int sizeReading: px(14)
    readonly property int sizeTitle: px(15)
    readonly property int sizeHeadline: px(19)
    readonly property int sizeMetric: px(20)

    readonly property font caption: Qt.font({"family": family, "pixelSize": sizeCaption})
    readonly property font small: Qt.font({"family": family, "pixelSize": sizeSmall})
    readonly property font smallStrong: Qt.font({"family": family, "pixelSize": sizeSmall, "weight": Font.DemiBold})
    readonly property font body: Qt.font({"family": family, "pixelSize": sizeBody})
    readonly property font bodyStrong: Qt.font({"family": family, "pixelSize": sizeBody, "weight": Font.DemiBold})
    readonly property font reading: Qt.font({"family": family, "pixelSize": sizeReading})
    readonly property font title: Qt.font({"family": family, "pixelSize": sizeTitle, "weight": Font.DemiBold})
    readonly property font headline: Qt.font({"family": family, "pixelSize": sizeHeadline, "weight": Font.DemiBold})
    readonly property font metric: Qt.font({"family": family, "pixelSize": sizeMetric, "weight": Font.DemiBold})
    readonly property font mono: Qt.font({"family": "Consolas", "pixelSize": sizeSmall})

    readonly property int hoverMs: 90
    readonly property bool motion: true
    readonly property int progressMs: motion ? 320 : 0
    readonly property int revealMs: motion ? 140 : 0
    readonly property color codeBackground: "#F2F4F6"
    readonly property int collapsedAnswer: px(168)
    readonly property int techMaxHeight: px(220)
    readonly property int narrowWidth: px(420)

    function ms(value)
    {
        return motion ? value : 0
    }

    property Component scrollStyle: Component
    {
        ScrollViewStyle
        {
            transientScrollBars: false
            decrementControl: Item { }
            incrementControl: Item { }
            corner: Item { }
            scrollBarBackground: Item
            {
                implicitWidth: px(10)
                implicitHeight: px(10)
            }
            handle: Item
            {
                implicitWidth: px(10)
                implicitHeight: px(10)

                Rectangle
                {
                    anchors.fill: parent
                    anchors.margins: px(2)
                    radius: px(3)
                    color: styleData.pressed ? "#8C96A0" : (styleData.hovered ? "#A7B0B9" : "#C6CDD4")
                }
            }
        }
    }
}
