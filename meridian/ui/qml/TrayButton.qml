import QtQuick
import QtQuick.Controls

// One button in one of the window's two icon bands: the header at the top or
// the tray at the foot.
//
// Extracted from main.qml, where seven of these were written out in full. They
// differed in their label, what they did and which button sat either side of
// them; everything else, including the four key handlers that make the band
// part of the focus ring, was copied seven times. It was HeaderButton until the
// footer wanted the same control at a smaller size; a second copy sized
// differently is how two bands stop matching.
//
// Neighbours are Items rather than signals here. Unlike the discovery panel's
// halves, these all live in one row and genuinely know each other, so naming
// the neighbour directly is both shorter and truthful. Leaving one unset is
// what marks the end of the row; the bar handles what happens there.
//
// The button is a mark and nothing else. The words that used to sit beside it
// are the tooltip now, which is also what a screen reader is given, so the one
// property carries the button's meaning wherever that meaning is asked for.
Rectangle {
    id: button

    required property var theme

    // The mark, as a URL relative to this file. The renders live in `art/`
    // beside the QML and are derived from the masters in `assets/` by
    // create_icons.py; build_resources.py holds the sizes and the names.
    property url iconSource: ""

    // What the button does, in words. Required in practice: a mark alone does
    // not say what pressing it will do, so a button without this is one nobody
    // can read.
    property string tooltip: ""

    property int iconSize: 54
    property int padding: 8

    // Which way the tooltip opens. The default is correct everywhere above the
    // fold and wrong at the foot of the window, where a tip six pixels below a
    // button that is itself a few pixels off the bottom renders off-screen.
    property bool tipBelow: true

    // The next and previous stops. Either may be null at the ends of the row.
    property Item nextItem: null
    property Item previousItem: null

    signal activated()

    // Emitted instead of moving focus when the neighbour in that direction is
    // not set, which is how the bar hands over to whatever is beyond it.
    signal forwardOverflow()
    signal backwardOverflow()

    // Square, so the row reads as an even set whatever each mark's own aspect
    // is. The mark is fitted inside rather than the box being fitted to it.
    width: iconSize + padding * 2
    height: iconSize + padding * 2
    radius: 8
    activeFocusOnTab: true
    color: buttonMouse.containsMouse ? theme.surface0 : theme.surface1
    border.color: (buttonMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
    border.width: 1

    // Named so the meaning survives for anyone not using a pointer.
    Accessible.role: Accessible.Button
    Accessible.name: button.tooltip

    // Declared rather than attached so it can wear the application's own
    // palette; the attached ToolTip takes the Fusion style's, which is a light
    // panel with dark text and reads as something borrowed in a dark window.
    // Declaring it means placing it too, hence the x and y below.
    //
    // Shown on hover and on keyboard focus alike, so the ring is readable
    // without a mouse. The delay is short deliberately: the mark is the only
    // thing on the button, so a tooltip that makes the user wait is the label
    // arriving late rather than a hint arriving on time.
    ToolTip {
        id: buttonTip
        objectName: "buttonTip"

        readonly property int gap: 6

        text: button.tooltip
        delay: 150
        visible: button.tooltip !== ""
                 && (buttonMouse.containsMouse || button.activeFocus)

        // Centred on the button, then held inside the window: the marks at
        // either end sit close enough to the edge that a centred tip would
        // otherwise hang off it.
        x: Math.round((button.width - width) / 2)
        y: button.tipBelow ? button.height + gap : -height - gap
        margins: 8
        padding: 8

        background: Rectangle {
            color: theme.surface0
            border.color: theme.surface1
            border.width: 1
            radius: 6
        }

        contentItem: Text {
            text: buttonTip.text
            color: theme.text
            font.pixelSize: 12
        }
    }

    function _forward() {
        if (button.nextItem) button.nextItem.forceActiveFocus(Qt.TabFocusReason)
        else button.forwardOverflow()
    }

    function _backward() {
        if (button.previousItem) button.previousItem.forceActiveFocus(Qt.BacktabFocusReason)
        else button.backwardOverflow()
    }

    Image {
        id: buttonIcon
        anchors.centerIn: parent

        // The marks are not square, so the drawn box is the mark's own aspect
        // at the requested height. Guarded because both implicit sizes read
        // zero until the source resolves.
        readonly property real aspect: implicitHeight > 0
                                       ? implicitWidth / implicitHeight
                                       : 1

        source: button.iconSource
        visible: button.iconSource != ""
        height: button.iconSize
        width: Math.round(button.iconSize * aspect)
        fillMode: Image.PreserveAspectFit
        smooth: true
        mipmap: true
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
