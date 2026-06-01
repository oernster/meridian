import QtQuick
import QtQuick.Controls

Button {
    id: root
    required property var theme
    property color textColor: theme.text

    implicitHeight: 32
    implicitWidth: contentItem.implicitWidth + 28

    contentItem: Text {
        text: root.text
        color: root.textColor
        font: root.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 7
        color: root.pressed ? root.theme.surface1
             : root.hovered ? root.theme.surface0
             : "transparent"
        border.color: root.hovered ? root.theme.amber : root.theme.surface0
        border.width: 1
    }
}
