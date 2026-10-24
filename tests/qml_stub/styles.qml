import QtQuick 2.2
import QtQuick.Controls 1.1
import QtQuick.Controls.Styles 1.1

QtObject
{
    property Component checkbox: Component { CheckBoxStyle { } }
    property Component text_field: Component { TextFieldStyle { } }
    property Component combobox: Component { ComboBoxStyle { } }
    property Component scrollview: Component { ScrollViewStyle { } }
}
