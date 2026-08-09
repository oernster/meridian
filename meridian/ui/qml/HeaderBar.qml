import QtQuick
import QtQuick.Controls

// The application header: file actions on the left, application actions and
// the theme toggle on the right.
//
// Extracted from main.qml. Every button is a HeaderButton now, so what remains
// here is the arrangement, the labels and the chain each button hands focus
// along. The bar reports what was pressed rather than acting: opening a file
// dialog or a drawer is the window's business, not the header's.
Rectangle {
    id: bar

    required property var theme

    // FeedReader wraps its own Tab chain back to this, so it needs the item
    // rather than a signal.
    readonly property alias firstFocusItem: importBtn

    signal importRequested()
    signal exportRequested()
    signal searchRequested()
    signal manageRequested()
    signal uiLicenceRequested()
    signal modelLicenceRequested()
    signal aboutRequested()
    signal themeToggleRequested()

    // Tab off the end of the row; Shift+Tab off the front of it.
    signal focusForwardRequested()
    signal focusBackwardRequested()

    function focusFirst() {
        importBtn.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusLast() {
        themeToggleBtn.forceActiveFocus(Qt.BacktabFocusReason)
    }

    height: 52
    color: theme.mantle

    // Left action row: Import | Export | separator | Search | Manage
    Row {
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        HeaderButton {
            id: importBtn
            objectName: "importBtn"
            theme: bar.theme
            label: "⬆  Import"
            nextItem: exportBtn
            onActivated: bar.importRequested()
            onBackwardOverflow: bar.focusBackwardRequested()
        }

        HeaderButton {
            id: exportBtn
            objectName: "exportBtn"
            theme: bar.theme
            label: "⬇  Export"
            nextItem: discoverBtn
            previousItem: importBtn
            onActivated: bar.exportRequested()
        }

        Rectangle {
            width: 1
            height: 24
            color: theme.surface1
            anchors.verticalCenter: parent.verticalCenter
        }

        HeaderButton {
            id: discoverBtn
            objectName: "discoverBtn"
            theme: bar.theme
            label: "🔍  Search"
            nextItem: manageBtn
            previousItem: exportBtn
            onActivated: bar.searchRequested()
        }

        HeaderButton {
            id: manageBtn
            objectName: "manageBtn"
            theme: bar.theme
            label: "⚙  Manage"
            nextItem: uiLicenceBtn
            previousItem: discoverBtn
            onActivated: bar.manageRequested()
        }
    }

    // Right action row: UI Licence | Model Licence | About | Theme toggle
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 6

        HeaderButton {
            id: uiLicenceBtn
            objectName: "uiLicenceBtn"
            theme: bar.theme
            label: "📜  UI Licence"
            nextItem: modelLicenceBtn
            previousItem: manageBtn
            onActivated: bar.uiLicenceRequested()
        }

        HeaderButton {
            id: modelLicenceBtn
            objectName: "modelLicenceBtn"
            theme: bar.theme
            label: "⚖️  Model Licence"
            nextItem: aboutBtn
            previousItem: uiLicenceBtn
            onActivated: bar.modelLicenceRequested()
        }

        HeaderButton {
            id: aboutBtn
            objectName: "aboutBtn"
            theme: bar.theme
            label: "ℹ️  About"
            nextItem: themeToggleBtn
            previousItem: modelLicenceBtn
            onActivated: bar.aboutRequested()
        }

        HeaderButton {
            id: themeToggleBtn
            objectName: "themeToggleBtn"
            theme: bar.theme
            label: bar.theme.isDark ? "☀️" : "🌙"
            fontSize: 16
            width: 40
            radius: 6
            previousItem: aboutBtn
            onActivated: bar.themeToggleRequested()
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
