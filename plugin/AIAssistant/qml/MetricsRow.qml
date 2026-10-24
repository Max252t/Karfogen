import QtQuick 2.2
import "."

Flow
{
    id: metrics
    property var items: []

    width: parent ? parent.width : implicitWidth
    spacing: Style.s5

    Repeater
    {
        model: metrics.items

        Column
        {
            spacing: Style.px(1)

            Text
            {
                text: modelData.value
                font: Style.metric
                color: Style.text
            }

            Text
            {
                text: modelData.label
                font: Style.small
                color: Style.textSecondary
            }
        }
    }
}
