import QtQuick
import QtQuick.Controls

// A transient confirmation strip: fades in, holds, fades out.
//
// Extracted from FeedDiscovery.qml, which carries far more than a screen
// should. The three-way dance between the hold timer and the two animations
// was spread across the caller and four sibling ids; it is one `show()` call
// from outside now, so a second caller cannot get the order wrong.
//
// Positioning is deliberately left to the caller. This anchors to nothing and
// assumes nothing about its parent, which is what makes it reusable.
Rectangle {
    id: toastBar

    // Show `message`, restarting the cycle if one is already running.
    function show(message) {
        label.text = message
        hideAnimation.stop()
        toastBar.opacity = 0
        showAnimation.start()
    }

    height: 40
    radius: 8
    color: theme.surface0
    border.color: theme.green
    border.width: 1
    opacity: 0
    visible: opacity > 0

    Label {
        id: label
        anchors.centerIn: parent
        color: theme.green
        font.pixelSize: 12
        font.bold: true
    }

    Timer {
        id: holdTimer
        interval: 2000
        onTriggered: hideAnimation.start()
    }

    NumberAnimation {
        id: showAnimation
        target: toastBar
        property: "opacity"
        to: 1.0
        duration: 180
        onStarted: holdTimer.restart()
    }

    NumberAnimation {
        id: hideAnimation
        target: toastBar
        property: "opacity"
        to: 0.0
        duration: 300
    }
}
