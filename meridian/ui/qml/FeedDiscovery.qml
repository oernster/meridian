import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The feed discovery drawer: header, search bar, results.
//
// This file is now the composition of the panel rather than the panel itself.
// It holds the state the two halves share (the search state, the selection and
// the error text), wires the halves to each other and to the controller, then
// owns the confirmations that a bulk subscribe needs. The search bar and the
// results know nothing about each other; every crossing goes through here.
Rectangle {
    id: root
    required property var theme
    signal close()

    color: theme.base
    Keys.onEscapePressed: root.close()

    property var selectedUrls: ({})
    property int selectedCount: 0

    property string _searchState: "idle"  // idle | searching | results | error | empty
    property string _errorMessage: ""
    property bool _hasMore: false

    readonly property var _capOptions: [10, 25, 50, 100, 200]
    readonly property int _defaultCapIndex: 1  // 25 results

    function _toggleUrl(url) {
        var s = Object.assign({}, selectedUrls)
        if (s[url]) { delete s[url] } else { s[url] = true }
        selectedUrls = s
        selectedCount = Object.keys(s).length
    }
    function _clearSelection() { selectedUrls = {}; selectedCount = 0 }

    Connections {
        target: controller
        function onSearchStarted() {
            root._searchState = "searching"
            root._errorMessage = ""
        }
        function onSearchFinished() {
            var n = controller.candidateModel.rowCount()
            root._searchState = n > 0 ? "results" : "empty"
            if (n > 0) {
                Qt.callLater(function() { resultsArea.focusListTop() })
            }
        }
        function onSearchError(msg) {
            root._searchState = "error"
            root._errorMessage = msg
        }
        function onSearchCancelled() {
            root._searchState = root._searchState === "results" ? "results" : "idle"
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: theme.mantle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 12

                Label {
                    text: "Discover Feeds"
                    font.pixelSize: 17
                    font.bold: true
                    color: theme.text
                    Layout.fillWidth: true
                }

                Button {
                    flat: true
                    implicitWidth: 36
                    implicitHeight: 36
                    onClicked: root.close()
                    contentItem: Label {
                        text: "✕"
                        color: theme.subtext
                        font.pixelSize: 15
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.pressed ? theme.surface1
                             : parent.hovered ? theme.surface0
                             : "transparent"
                        border.color: parent.hovered ? theme.amber : "transparent"
                        border.width: 1
                        radius: 6
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.surface0
            }
        }

        DiscoverySearchBar {
            id: searchBar
            objectName: "searchBar"
            Layout.fillWidth: true
            theme: root.theme
            searchState: root._searchState
            capOptions: root._capOptions
            capIndex: root._defaultCapIndex

            onSearchRequested: root._doSearch()
            onCancelRequested: controller.cancelSearch()
            onCloseRequested: root.close()
            onCapChosen: function(cap) { controller.setResultCap(cap) }
            onFocusForwardRequested: resultsArea.focusFirst()
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme.surface0
        }

        DiscoveryResults {
            id: resultsArea
            objectName: "resultsArea"
            Layout.fillWidth: true
            Layout.fillHeight: true
            theme: root.theme
            searchState: root._searchState
            errorMessage: root._errorMessage
            hasMore: root._hasMore
            candidateModel: controller ? controller.candidateModel : null
            selectedUrls: root.selectedUrls
            selectedCount: root.selectedCount

            onToggleRequested: function(url) { root._toggleUrl(url) }
            onSubscribeRequested: function(url, title) {
                controller.subscribeFromDiscovery(url)
                root._showSingleToast(title)
            }
            onBulkSubscribeRequested: bulkConfirmDialog.open()
            onFocusForwardRequested: searchBar.focusFirst()
            onFocusBackwardRequested: searchBar.focusLast()
        }
    }

    // Bulk subscribe confirmation dialog
    UrlListDialog {
        id: bulkConfirmDialog
        title: "Subscribe to Feeds"
        heading: "Subscribe to " + root.selectedCount + " feed(s)?"
        urls: Object.keys(root.selectedUrls)

        StyledButton {
            id: discoveryCancelBtn
            text: "Cancel"; theme: root.theme; onClicked: bulkConfirmDialog.reject()
            Keys.onReturnPressed: { bulkConfirmDialog.reject(); event.accepted = true }
            Keys.onRightPressed: { discoverySubscribeBtn.forceActiveFocus(); event.accepted = true }
        }
        StyledButton {
            id: discoverySubscribeBtn
            text: "Subscribe"; theme: root.theme; onClicked: bulkConfirmDialog.accept()
            Keys.onReturnPressed: { bulkConfirmDialog.accept(); event.accepted = true }
            Keys.onLeftPressed: { discoveryCancelBtn.forceActiveFocus(); event.accepted = true }
        }

        onAccepted: {
            var urls = Object.keys(root.selectedUrls)
            controller.bulkSubscribeFromDiscovery(urls)
            root._clearSelection()
            bulkResultDialog.urls = urls
            bulkResultDialog.open()
        }
    }

    // Bulk subscribe result dialog
    UrlListDialog {
        id: bulkResultDialog
        title: "Subscribed"
        heading: "Subscribed to " + bulkResultDialog.urls.length + " feed(s):"

        StyledButton {
            text: "OK"
            theme: root.theme
            onClicked: bulkResultDialog.accept()
            Keys.onReturnPressed: { bulkResultDialog.accept(); event.accepted = true }
        }
    }

    // Single-subscribe toast
    ToastBar {
        id: toastBar
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.margins: 16
        anchors.bottomMargin: 16
    }

    function focusSearch() { searchBar.focusFirst() }

    function _doSearch() {
        var q = searchBar.queryText.trim()
        if (q.length === 0) return
        root._clearSelection()
        controller.searchFeeds(q)
    }

    function _showSingleToast(title) {
        toastBar.show("Subscribed to " + title)
    }
}
