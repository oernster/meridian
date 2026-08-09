import QtQuick
import QtQuick.Controls

// One button on the application header bar.
//
// Extracted from main.qml, where seven of these were written out in full. They
// differed in their label, what they did and which button sat either side of
// them; everything else, including the four key handlers that make the header
// part of the focus ring, was copied seven times.
//
// Neighbours are Items rather than signals here. Unlike the discovery panel's
// halves, these all live in one row and genuinely know each other, so naming
// the neighbour directly is both shorter and truthful. Leaving one unset is
// what marks the end of the row; the bar handles what happens there.
Rectangle {
    id: button

    required property var theme
    property string label: ""

    // The theme toggle carries a glyph rather than words, so it sets its own
    // size and a fixed width instead of sizing to its text.
    property int fontSize: 13

    // The next and previous stops. Either may be null at the ends of the row.
    property Item nextItem: null
    property Item previousItem: null

    signal activated()

    // Emitted instead of moving focus when the neighbour in that direction is
    // not set, which is how the bar hands over to whatever is beyond it.
    signal forwardOverflow()
    signal backwardOverflow()

    width: buttonLabel.contentWidth + 20
    height: 34
    radius: 8
    activeFocusOnTab: true
    color: buttonMouse.containsMouse ? theme.surface0 : theme.surface1
    border.color: (buttonMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
    border.width: 1

    function _forward() {
        if (button.nextItem) button.nextItem.forceActiveFocus(Qt.TabFocusReason)
        else button.forwardOverflow()
    }

    function _backward() {
        if (button.previousItem) button.previousItem.forceActiveFocus(Qt.BacktabFocusReason)
        else button.backwardOverflow()
    }

    Label {
        id: buttonLabel
        anchors.centerIn: parent
        text: button.label
        font.pixelSize: button.fontSize
        color: theme.text
    }

    MouseArea {
        id: buttonMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: button.activated()
    }

    Keys.onReturnPressed: button.activated()
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Space) {
            button.activated()
            event.accepted = true
        }
    }
    Keys.onTabPressed:     { event.accepted = true; button._forward() }
    Keys.onRightPressed:   { event.accepted = true; button._forward() }
    Keys.onBacktabPressed: { event.accepted = true; button._backward() }
    Keys.onLeftPressed:    { event.accepted = true; button._backward() }
}
