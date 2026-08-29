import QtQuick
import QtQuick.Controls

// The application header: file actions on the left, application actions and
// the theme toggle on the right.
//
// Extracted from main.qml. Every button is a TrayButton now, so what remains
// here is the arrangement, the marks and the chain each button hands focus
// along. The bar reports what was pressed rather than acting: opening a file
// dialog or a drawer is the window's business, not the header's.
//
// The marks are files rather than emoji. An emoji is drawn by whichever font
// the platform picks, so the row looked different on each of the three the
// application ships to; a render is the same picture everywhere.
//
// The two licences used to sit here and sit in the foot now. They say what is
// true of the application rather than acting on what is being read, which is
// what everything left on this bar does.
Rectangle {
    id: bar

    required property var theme

    // FeedReader wraps its own Tab chain back to this, so it needs the item
    // rather than a signal.
    readonly property alias firstFocusItem: importBtn

    // The foot's mark is a fraction of this, taken from here rather than named
    // again, so retuning the header carries the foot with it.
    readonly property int markSize: importBtn.iconSize

    signal importRequested()
    signal exportRequested()
    signal searchRequested()
    signal manageRequested()
    signal specificationRequested()
    signal aboutRequested()
    signal themeToggleRequested()

    // Tab off the end of the row; Shift+Tab off the front of it.
    signal focusForwardRequested()
    signal focusBackwardRequested()

    function focusFirst() {
        importBtn.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusLast() {
        aboutBtn.forceActiveFocus(Qt.BacktabFocusReason)
    }

    height: 82
    color: theme.mantle

    // Left action row: Import | Export | separator | Search | Manage
    Row {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        TrayButton {
            id: importBtn
            objectName: "importBtn"
            theme: bar.theme
            iconSource: "art/import.png"
            tooltip: "Import subscriptions from a file"
            nextItem: exportBtn
            onActivated: bar.importRequested()
            onBackwardOverflow: bar.focusBackwardRequested()
        }

        TrayButton {
            id: exportBtn
            objectName: "exportBtn"
            theme: bar.theme
            iconSource: "art/export.png"
            tooltip: "Export subscriptions to a file"
            nextItem: discoverBtn
            previousItem: importBtn
            onActivated: bar.exportRequested()
        }

        Rectangle {
            width: 1
            height: 48
            color: theme.surface1
            anchors.verticalCenter: parent.verticalCenter
        }

        TrayButton {
            id: discoverBtn
            objectName: "discoverBtn"
            theme: bar.theme
            iconSource: "art/search.png"
            tooltip: "Find feeds to subscribe to"
            nextItem: manageBtn
            previousItem: exportBtn
            onActivated: bar.searchRequested()
        }

        TrayButton {
            id: manageBtn
            objectName: "manageBtn"
            theme: bar.theme
            iconSource: "art/manage.png"
            tooltip: "Manage subscriptions"
            nextItem: specBtn
            previousItem: discoverBtn
            onActivated: bar.manageRequested()
        }
    }

    // Right action row: Specification | Theme toggle | About
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        TrayButton {
            id: specBtn
            objectName: "specBtn"
            theme: bar.theme
            iconSource: "art/specification.png"
            tooltip: "Read the MMSP specification (opens your browser)"
            nextItem: themeToggleBtn
            previousItem: manageBtn
            onActivated: bar.specificationRequested()
        }

        TrayButton {
            id: themeToggleBtn
            objectName: "themeToggleBtn"
            theme: bar.theme
            iconSource: bar.theme.isDark ? "art/light-mode.png"
                                         : "art/dark-mode.png"
            tooltip: bar.theme.isDark ? "Switch to the light palette"
                                      : "Switch to the dark palette"
            nextItem: aboutBtn
            previousItem: specBtn
            onActivated: bar.themeToggleRequested()
        }

        TrayButton {
            id: aboutBtn
            objectName: "aboutBtn"
            theme: bar.theme
            iconSource: "art/help.png"
            tooltip: "About Meridian"
            previousItem: themeToggleBtn
            onActivated: bar.aboutRequested()
            onForwardOverflow: bar.focusForwardRequested()
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: theme.surface0
    }
}
