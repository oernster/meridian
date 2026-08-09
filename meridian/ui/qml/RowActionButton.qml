import QtQuick
import QtQuick.Controls

// A small flat action on a list row: Filter, Edit, Remove.
//
// Extracted from SubscriptionManager.qml, where the three were written out in
// full and differed only in their label, their colour and what they did.
//
// Neighbours are Items rather than signals: all three sit in one row and
// genuinely know each other, so naming the neighbour is shorter and truthful.
// Leaving one unset is what marks the end of the row.
Button {
    id: action

    required property var theme
    property color labelColour: theme.blue

    property Item nextItem: null
    property Item previousItem: null

    flat: true
    font.pixelSize: 11
    implicitHeight: 26
    implicitWidth: 52

    contentItem: Label {
        text: action.text
        color: action.labelColour
        font.pixelSize: 11
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        color: action.pressed ? theme.surface1
             : action.hovered ? theme.surface0
             : "transparent"
        border.color: (action.activeFocus || action.hovered) ? theme.amber : theme.surface0
        border.width: 1
        radius: 5
    }

    Keys.onReturnPressed: {
        action.clicked()
        event.accepted = true
    }
    Keys.onLeftPressed: {
        if (action.previousItem) action.previousItem.forceActiveFocus()
        event.accepted = true
    }
    Keys.onRightPressed: {
        if (action.nextItem) action.nextItem.forceActiveFocus()
        event.accepted = true
    }
}
