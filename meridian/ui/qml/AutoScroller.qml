import QtQuick

// Long content that reads itself: it holds still while the reader orients,
// descends slowly, holds at the end, rewinds fast and repeats.
//
// Attach one to any Flickable. A ScrollView's `contentItem` is a Flickable and
// a ListView is one itself, so both kinds of surface wear the same object.
//
// Two rules the pace depends on. There is ONE pace for every surface in the
// application, so these constants live here and a caller never overrides one:
// if a surface needs a different pace, the pace is wrong everywhere. And a
// reader who takes hold SUSPENDS the cycle rather than switching it off, so it
// picks up from wherever they left it, in whichever direction still has room.
QtObject {
    id: scroller

    // The surface that scrolls.
    required property Flickable flick

    // False FREEZES the cycle rather than stopping it: the tick returns before
    // touching the wait, so the phase, the position and whatever is left of
    // the current hold are all exactly where they were when it resumes. A
    // caller clears this while its surface is not the one being read, which
    // means at least while the dialog is closed and also whenever a modal sits
    // above it, because two surfaces reading at once compete for the eye.
    property bool active: false

    // The surface's scrollbar, where it has a named one. A press that never
    // moves anything cannot be seen as a change of position; it is still a
    // reader taking hold.
    property var scrollBar: null

    readonly property int tickMs: 40
    readonly property int startHoldMs: 5000
    readonly property int bottomHoldMs: 5000
    readonly property int topHoldMs: 2000
    readonly property int manualHoldMs: 2500
    readonly property int descentPx: 1
    readonly property int ticksPerStep: 2
    readonly property int rewindPx: 15

    // The descent advances every second tick rather than running a slower
    // timer, so every wait keeps its 40ms granularity.
    property string phase: "pauseTop"
    property int wait: startHoldMs
    property int _stepsLeft: ticksPerStep
    property real _placedAt: 0

    // True until the opening hold is spent. A surface that focuses something
    // inside itself as it opens (the licence dialog focuses its text so the
    // keys work at once) would otherwise read that as a reader taking hold and
    // cut the opening hold in half.
    property bool _opening: true

    signal suspended()

    // A frozen surface has no reader, so nothing that reaches it while it is
    // inactive can be one. A closing popup returns its view to the top as
    // focus leaves with it. Acting on those would corrupt the very phase
    // the freeze exists to preserve.
    function suspend() {
        if (!scroller.active) return
        scroller.phase = "manual"
        scroller.wait = scroller.manualHoldMs
        scroller.suspended()
    }

    // Every fresh surface holds still before its first descent.
    function restart() {
        scroller.phase = "pauseTop"
        scroller.wait = scroller.startHoldMs
        scroller._stepsLeft = scroller.ticksPerStep
        scroller._opening = true
        scroller._placedAt = scroller.flick ? scroller.flick.contentY : 0
    }

    function maximumY() {
        return Math.max(0, scroller.flick.contentHeight - scroller.flick.height)
    }

    function tick() {
        if (!scroller.active || !scroller.flick) return
        // Attaching this to a surface that currently fits is free: nothing
        // overflows, so nothing moves and no wait is spent.
        if (scroller.maximumY() <= 0) return

        if (scroller.wait > 0) {
            scroller.wait -= scroller.tickMs
            if (scroller.wait <= 0) {
                scroller.phase = scroller._resumeInto()
                scroller._opening = false
            }
            return
        }
        if (scroller.phase === "down") scroller._descend()
        else if (scroller.phase === "up") scroller._rewind()
    }

    // After the bottom hold there is only one way to go. After a manual hold
    // at the very bottom the same is true; anywhere else the reader was
    // heading down.
    function _resumeInto() {
        if (scroller.phase === "pauseBottom") return "up"
        if (scroller.phase === "manual" && scroller.flick.contentY >= scroller.maximumY())
            return "up"
        return "down"
    }

    function _descend() {
        scroller._stepsLeft -= 1
        if (scroller._stepsLeft > 0) return
        scroller._stepsLeft = scroller.ticksPerStep
        if (scroller._placeAt(scroller.flick.contentY + scroller.descentPx)
                >= scroller.maximumY()) {
            scroller.phase = "pauseBottom"
            scroller.wait = scroller.bottomHoldMs
        }
    }

    // A reposition rather than a reading pass, so it travels.
    function _rewind() {
        if (scroller._placeAt(scroller.flick.contentY - scroller.rewindPx) <= 0) {
            scroller.phase = "pauseTop"
            scroller.wait = scroller.topHoldMs
        }
    }

    function _placeAt(y) {
        var clamped = Math.max(0, Math.min(y, scroller.maximumY()))
        scroller._placedAt = clamped
        scroller.flick.contentY = clamped
        return clamped
    }

    function _holdsFocus(item) {
        while (item) {
            if (item === scroller.flick) return true
            item = item.parent
        }
        return false
    }

    onActiveChanged: if (scroller.active) scroller.restart()

    // Named so a test can hold the machine still and advance it by hand: every
    // phase is measured in whole ticks; waiting five real seconds for the
    // opening hold would be slow and flaky both.
    property Timer _ticker: Timer {
        objectName: "autoScrollTicker"
        interval: scroller.tickMs
        repeat: true
        running: true
        onTriggered: scroller.tick()
    }

    // One watch covers every way a reader can move the surface by hand: the
    // wheel, a drag, a flick, the scrollbar and the keys all arrive here as a
    // position this object did not place.
    property Connections _moved: Connections {
        target: scroller.flick
        function onContentYChanged() {
            // A frozen surface has no reader, so movement there is the toolkit
            // rather than a hand: a closing popup returns its view to the top.
            // Taking that as manual input would corrupt the phase the freeze
            // exists to preserve, so it is only followed, never acted on.
            if (!scroller.active) {
                scroller._placedAt = scroller.flick.contentY
                return
            }
            if (Math.abs(scroller.flick.contentY - scroller._placedAt) > 0.5)
                scroller.suspend()
        }
    }

    property Connections _grabbed: Connections {
        target: scroller.scrollBar
        function onPressedChanged() { scroller.suspend() }
    }

    // Focus reaching the surface is a reader arriving by keyboard, so it
    // suspends exactly as a scroll does. A child never sees the surface's own
    // handlers, which is why this asks the window and walks back up.
    property Connections _focused: Connections {
        target: scroller.flick ? scroller.flick.Window.window : null
        function onActiveFocusItemChanged() {
            if (scroller._opening) return
            if (scroller._holdsFocus(scroller.flick.Window.window.activeFocusItem))
                scroller.suspend()
        }
    }
}
