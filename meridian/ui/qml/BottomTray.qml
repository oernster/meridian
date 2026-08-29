import QtQuick

// The strip along the foot of the window: the donate button, then the two
// licences.
//
// Its own band rather than seats in the header, because none of these three
// acts on what is being read. Everything on the header opens a file, a drawer
// or a dialog about the feeds; donate leaves the application entirely and the
// licences state what is true of the application itself, so they sit together
// where nothing else is reached by accident. Donate is first and leftmost: it
// is the only one that opens a browser.
//
// The band takes the header's mark height rather than measuring or naming one
// of its own, then draws two thirds of it. That is ClearBudget's rule and its
// reason carries: the header is the heaviest band on the window, so a matching
// foot would weigh the layout down at both ends, while two thirds still leaves
// the artwork big enough to recognise. Deriving one number twice is how two
// bands drift, so the numerator and the denominator are here and the height is
// not.
Rectangle {
    id: tray

    required property var theme

    // The header's mark height, passed in by the window that owns both bands.
    required property int headerMarkSize

    signal donateRequested()
    signal uiLicenceRequested()
    signal modelLicenceRequested()

    // Tab off the end of the strip; Shift+Tab off the front of it.
    signal focusForwardRequested()
    signal focusBackwardRequested()

    readonly property alias firstFocusItem: donateBtn

    function focusFirst() {
        donateBtn.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusLast() {
        modelLicenceBtn.forceActiveFocus(Qt.BacktabFocusReason)
    }

    // build_resources.FOOTER_NUMERATOR and FOOTER_DENOMINATOR; a structural
    // test holds the two statements of the ratio to each other.
    readonly property int _footerNumerator: 2
    readonly property int _footerDenominator: 3
    readonly property int markSize: Math.max(
        1, Math.floor(headerMarkSize * _footerNumerator / _footerDenominator))

    // Half the header's, for the same reason the mark is two thirds: this is
    // the lighter of the two bands.
    readonly property int edgePadding: 5
    readonly property int buttonPadding: 5

    height: donateBtn.height + edgePadding * 2
    color: theme.mantle

    Rectangle {
        anchors.top: parent.top
        width: parent.width
        height: 1
        color: theme.surface0
    }

    Row {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        // Every tooltip on this band opens upward: a tip six pixels below a
        // button whose own bottom sits five pixels off the window renders
        // off-screen.
        TrayButton {
            id: donateBtn
            objectName: "donateBtn"
            theme: tray.theme
            iconSize: tray.markSize
            padding: tray.buttonPadding
            tipBelow: false
            iconSource: "art/donate.png"
            tooltip: "Buy the author a drink (opens your browser)"
            nextItem: uiLicenceBtn
            onActivated: tray.donateRequested()
            onBackwardOverflow: tray.focusBackwardRequested()
        }

        TrayButton {
            id: uiLicenceBtn
            objectName: "uiLicenceBtn"
            theme: tray.theme
            iconSize: tray.markSize
            padding: tray.buttonPadding
            tipBelow: false
            iconSource: "art/ui-licence.png"
            tooltip: "UI licence: LGPL-3.0"
            nextItem: modelLicenceBtn
            previousItem: donateBtn
            onActivated: tray.uiLicenceRequested()
        }

        TrayButton {
            id: modelLicenceBtn
            objectName: "modelLicenceBtn"
            theme: tray.theme
            iconSize: tray.markSize
            padding: tray.buttonPadding
            tipBelow: false
            iconSource: "art/model-licence.png"
            tooltip: "Model licence: Apache-2.0"
            previousItem: uiLicenceBtn
            onActivated: tray.modelLicenceRequested()
            onForwardOverflow: tray.focusForwardRequested()
        }
    }
}
