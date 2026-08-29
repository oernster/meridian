import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Qt.labs.settings

// The application window: composition, shared state and the things that belong
// to no single panel.
//
// What is left here after the split is the feed selection (which the sidebar
// displays, the context menu acts on and the removal confirmations consume),
// the palette, plus the wiring from each panel's signals to the controller. The
// header, the sidebar and the reader know nothing about each other; the focus
// ring passes between them through this file.
ApplicationWindow {
    id: root
    title: "Meridian"
    width: 1280
    height: 800
    minimumWidth: 920
    minimumHeight: 580
    visible: true

    Settings {
        id: appSettings
        category: "Theme"
        property bool isDark: true
    }

    Settings {
        id: updateSettings
        objectName: "updateSettings"
        category: "Updates"
        // The exact release tag the user chose to skip; that version never
        // prompts again. The manual check ignores it by construction.
        property string skippedVersion: ""
    }

    // The launch check waits so it never contends with startup work; the
    // periodic re-check covers sessions that stay open for days.
    readonly property int _updateLaunchDelayMs: 3000
    readonly property int _updateRecheckIntervalMs: 24 * 60 * 60 * 1000

    Timer {
        interval: root._updateLaunchDelayMs
        running: true
        onTriggered: updateController.checkAutomatically(updateSettings.skippedVersion)
    }

    Timer {
        interval: root._updateRecheckIntervalMs
        running: true
        repeat: true
        onTriggered: updateController.checkAutomatically(updateSettings.skippedVersion)
    }

    Theme {
        id: theme
        isDark: appSettings.isDark
    }

    color: theme.base

    property var _selectedFeedIds: ({})
    property int _selectedFeedCount: 0

    function _toggleFeed(feedId) {
        var s = Object.assign({}, _selectedFeedIds)
        if (s[feedId]) { delete s[feedId] } else { s[feedId] = true }
        _selectedFeedIds = s
        _selectedFeedCount = Object.keys(s).length
    }

    function _selectAllFeeds() {
        var s = {}
        var m = controller.feedModel
        for (var i = 0; i < m.rowCount(); i++) {
            s[m.data(m.index(i, 0), Qt.UserRole)] = true
        }
        _selectedFeedIds = s
        _selectedFeedCount = Object.keys(s).length
    }

    function _clearFeedSelection() { _selectedFeedIds = {}; _selectedFeedCount = 0 }

    function _selectedFeedIdList() {
        return Object.keys(root._selectedFeedIds).map(function(k) { return parseInt(k) })
    }

    function _confirmBulkRemoval() {
        bulkRemoveDialog.pendingIds = root._selectedFeedIdList()
        bulkRemoveDialog.open()
    }

    Component.onCompleted: controller.loadFeeds()

    Connections {
        target: controller
        function onErrorOccurred(msg) {
            errorDialog.message = msg
            errorDialog.open()
        }
        function onNewItemsAvailable(feedId, count) { }
    }

    // Absorbs initial focus so no item shows an orange border on startup.
    // First Tab press explicitly navigates to the header.
    Item {
        id: initialFocusItem
        objectName: "initialFocusItem"
        focus: true
        activeFocusOnTab: false
        width: 0; height: 0
        Keys.onTabPressed: { event.accepted = true; header.focusFirst() }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        HeaderBar {
            id: header
            objectName: "header"
            Layout.fillWidth: true
            theme: theme

            onImportRequested: importDialog.open()
            onExportRequested: exportDialog.open()
            onSearchRequested: feedDiscoveryDrawer.open()
            onManageRequested: subManagerDrawer.open()
            onSpecificationRequested: linksController.openSpecification()
            onAboutRequested: aboutDialog.open()
            onThemeToggleRequested: {
                theme.isDark = !theme.isDark
                appSettings.isDark = theme.isDark
            }

            onFocusForwardRequested: sidebar.focusFirst()
            onFocusBackwardRequested: bottomTray.focusLast()
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            FeedSidebar {
                id: sidebar
                objectName: "sidebar"
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                theme: theme
                feedModel: controller.feedModel
                selectedFeedIds: root._selectedFeedIds
                selectedCount: root._selectedFeedCount

                onToggleRequested: function(feedId) { root._toggleFeed(feedId) }
                onSelectAllRequested: root._selectAllFeeds()
                onClearSelectionRequested: root._clearFeedSelection()
                onRemoveSelectedRequested: root._confirmBulkRemoval()
                onSortChosen: function(key) { controller.setFeedSort(key) }
                onFeedActivated: function(feedId) { controller.selectFeed(feedId) }
                onContextMenuRequested: function(feedId, title, globalX, globalY) {
                    feedContextMenu.targetFeedId = feedId
                    feedContextMenu.targetTitle = title
                    feedContextMenu.openAt(globalX, globalY)
                }
                onFocusBackwardRequested: header.focusLast()
            }

            // Divider
            Rectangle {
                width: 1
                Layout.fillHeight: true
                color: theme.surface0
            }

            FeedReader {
                id: feedReader
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: theme
                wrapForwardItem: bottomTray.firstFocusItem
            }
        }

        BottomTray {
            id: bottomTray
            objectName: "bottomTray"
            Layout.fillWidth: true
            theme: theme
            headerMarkSize: header.markSize

            onDonateRequested: linksController.openDonation()
            onUiLicenceRequested: uiLicenceDialog.open()
            onModelLicenceRequested: modelLicenceDialog.open()
            onFocusForwardRequested: header.focusFirst()
            onFocusBackwardRequested: feedReader.lastFocusItem.forceActiveFocus(Qt.BacktabFocusReason)
        }
    }

    FeedContextMenu {
        id: feedContextMenu
        objectName: "feedContextMenu"
        theme: theme
        selectedCount: root._selectedFeedCount

        onRemoveRequested: {
            removeDialog.targetFeedId = feedContextMenu.targetFeedId
            removeDialog.message = "Remove \"" + feedContextMenu.targetTitle
                                 + "\"?\nAll downloaded items will be deleted."
            removeDialog.open()
        }
        // Deferred: opening straight out of the menu's own close lands the
        // dialog underneath the overlay that is still tearing down.
        onRemoveSelectedRequested: Qt.callLater(root._confirmBulkRemoval)
    }

    ConfirmDialog {
        id: removeDialog
        objectName: "removeDialog"
        theme: theme
        title: "Remove Feed"
        property int targetFeedId: 0
        onAccepted: controller.unsubscribe(removeDialog.targetFeedId)
    }

    ConfirmDialog {
        id: bulkRemoveDialog
        objectName: "bulkRemoveDialog"
        theme: theme
        title: "Remove Feeds"
        property var pendingIds: []
        message: "Remove " + bulkRemoveDialog.pendingIds.length
               + " feed(s)?\nAll downloaded items will be deleted."
        onAccepted: {
            root._clearFeedSelection()
            controller.bulkUnsubscribe(bulkRemoveDialog.pendingIds)
        }
    }

    ConfirmDialog {
        id: errorDialog
        objectName: "errorDialog"
        theme: theme
        title: "Error"
        okOnly: true
        bodyLineHeight: 1.0
    }

    Drawer {
        id: subManagerDrawer
        width: Math.min(520, root.width * 0.46)
        height: root.height
        edge: Qt.RightEdge
        onOpened: subManager.focusUrlField()

        SubscriptionManager {
            id: subManager
            anchors.fill: parent
            theme: theme
            onClose: subManagerDrawer.close()
        }
    }

    Drawer {
        id: feedDiscoveryDrawer
        width: Math.min(560, root.width * 0.50)
        height: root.height
        edge: Qt.RightEdge

        onClosed: controller.cancelSearch()
        onOpened: feedDiscovery.focusSearch()

        FeedDiscovery {
            id: feedDiscovery
            anchors.fill: parent
            theme: theme
            onClose: feedDiscoveryDrawer.close()
        }
    }

    AboutDialog {
        id: aboutDialog
        objectName: "aboutDialog"
        theme: theme
        onCheckUpdatesRequested: updateController.checkManually()
    }

    Connections {
        target: linksController
        function onOpenFailed(what) {
            errorDialog.message = "Could not open a browser for " + what + "."
            errorDialog.open()
        }
    }

    Connections {
        target: updateController
        function onUpdateAvailable(latest, current, downloadUrl, pageUrl) {
            updateDialog.latestVersion = latest
            updateDialog.currentVersion = current
            updateDialog.downloadUrl = downloadUrl
            updateDialog.pageUrl = pageUrl
            updateDialog.open()
        }
        function onUpToDate() {
            updateInfoDialog.message = "You are running the latest version."
            updateInfoDialog.open()
        }
        function onCheckFailed() {
            updateInfoDialog.message = "The update check could not reach GitHub. "
                                     + "Please try again later."
            updateInfoDialog.open()
        }
    }

    UpdateDialog {
        id: updateDialog
        objectName: "updateDialog"
        theme: theme
        onDownloadRequested: updateController.openDownload(
            updateDialog.downloadUrl !== "" ? updateDialog.downloadUrl
                                            : updateDialog.pageUrl)
        onSkipRequested: updateSettings.skippedVersion = updateDialog.latestVersion
    }

    ConfirmDialog {
        id: updateInfoDialog
        objectName: "updateInfoDialog"
        theme: theme
        title: "Check for Updates"
        okOnly: true
        bodyLineHeight: 1.0
    }

    LicenceDialog {
        id: uiLicenceDialog
        theme: theme
        licenceTitle: "UI Licence - GNU Lesser General Public Licence v3.0"
        licenceBody: uiLicenceText
    }

    LicenceDialog {
        id: modelLicenceDialog
        theme: theme
        licenceTitle: "Model Licence - Apache License 2.0"
        licenceBody: modelLicenceText
    }

    FileDialog {
        id: exportDialog
        fileMode: FileDialog.SaveFile
        nameFilters: ["Meridian feeds (*.json)"]
        defaultSuffix: "json"
        onAccepted: controller.exportFeeds(selectedFile)
    }

    FileDialog {
        id: importDialog
        fileMode: FileDialog.OpenFile
        nameFilters: ["Meridian feeds (*.json)", "All files (*)"]
        onAccepted: controller.importFeeds(selectedFile)
    }
}
