import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

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
    property int _capIndex: 1  // default 25

    property var _suggestions: []
    property var _currentXhr: null

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
                Qt.callLater(function() {
                    resultsList.currentIndex = 0
                    resultsList.forceActiveFocus(Qt.TabFocusReason)
                })
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

        // Search section
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: searchCol.implicitHeight + 32
            color: theme.mantle

            ColumnLayout {
                id: searchCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 10

                Label {
                    text: "Search by Category or Topic"
                    font.pixelSize: 13
                    font.bold: true
                    color: theme.subtext
                    font.letterSpacing: 0.6
                }

                // Query field + autocomplete popup
                Item {
                    Layout.fillWidth: true
                    implicitHeight: queryField.implicitHeight

                    TextField {
                        id: queryField
                        width: parent.width
                        placeholderText: "e.g. Python, Technology, Science..."
                        color: theme.text
                        placeholderTextColor: theme.overlay
                        font.pixelSize: 13
                        background: Rectangle {
                            color: theme.base
                            border.color: queryField.activeFocus ? theme.blue : theme.surface1
                            border.width: queryField.activeFocus ? 2 : 1
                            radius: 6
                        }
                        leftPadding: 10
                        rightPadding: 10
                        topPadding: 8
                        bottomPadding: 8

                        Keys.onReturnPressed: function(event) {
                            if (autocompletePopup.visible && autocompleteList.currentIndex >= 0) {
                                queryField.text = autocompleteList.model[autocompleteList.currentIndex]
                                autocompleteList.currentIndex = -1
                                autocompletePopup.close()
                            } else {
                                _doSearch()
                            }
                            event.accepted = true
                        }
                        Keys.onDownPressed: function(event) {
                            if (autocompletePopup.visible) {
                                autocompleteList.currentIndex = Math.min(
                                    autocompleteList.currentIndex + 1,
                                    autocompleteList.count - 1
                                )
                                autocompleteList.positionViewAtIndex(
                                    autocompleteList.currentIndex, ListView.Contain
                                )
                                event.accepted = true
                            }
                        }
                        Keys.onUpPressed: function(event) {
                            if (autocompletePopup.visible) {
                                autocompleteList.currentIndex = Math.max(
                                    autocompleteList.currentIndex - 1, -1
                                )
                                if (autocompleteList.currentIndex >= 0) {
                                    autocompleteList.positionViewAtIndex(
                                        autocompleteList.currentIndex, ListView.Contain
                                    )
                                }
                                event.accepted = true
                            }
                        }
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Space
                                    && autocompletePopup.visible
                                    && autocompleteList.currentIndex >= 0) {
                                queryField.text = autocompleteList.model[autocompleteList.currentIndex]
                                autocompleteList.currentIndex = -1
                                autocompletePopup.close()
                                event.accepted = true
                            }
                        }
                        Keys.onTabPressed: function(event) {
                            event.accepted = true
                            if (autocompletePopup.visible) {
                                autocompleteList.currentIndex = -1
                                autocompletePopup.close()
                            }
                            capCombo.forceActiveFocus(Qt.TabFocusReason)
                        }
                        Keys.onEscapePressed: {
                            if (autocompletePopup.visible) {
                                autocompleteList.currentIndex = -1
                                autocompletePopup.close()
                            } else if (root._searchState === "searching") {
                                controller.cancelSearch()
                            } else {
                                root.close()
                            }
                        }
                        onTextChanged: {
                            autocompleteList.currentIndex = -1
                            if (text.trim().length >= 2) {
                                autocompleteDebounce.restart()
                            } else {
                                autocompleteDebounce.stop()
                                root._suggestions = []
                                autocompletePopup.close()
                            }
                        }
                    }

                    Popup {
                        id: autocompletePopup
                        y: queryField.height + 2
                        width: queryField.width
                        padding: 4
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
                        background: Rectangle {
                            color: theme.mantle
                            border.color: theme.surface0
                            border.width: 1
                            radius: 6
                        }

                        contentItem: ListView {
                            id: autocompleteList
                            currentIndex: -1
                            implicitHeight: Math.min(contentHeight, 180)
                            clip: true
                            model: root._suggestions
                            delegate: Rectangle {
                                width: autocompleteList.width
                                height: 32
                                color: (index === autocompleteList.currentIndex || acHover.containsMouse)
                                       ? theme.surface0 : "transparent"
                                radius: 4
                                Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 8
                                    text: modelData
                                    color: index === autocompleteList.currentIndex
                                           ? theme.blue : theme.text
                                    font.pixelSize: 13
                                    font.bold: index === autocompleteList.currentIndex
                                }
                                MouseArea {
                                    id: acHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        autocompleteList.currentIndex = -1
                                        queryField.text = modelData
                                        autocompletePopup.close()
                                        queryField.forceActiveFocus()
                                    }
                                }
                            }
                        }
                    }
                }

                // Cap selector row + Search/Cancel button
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Label {
                        text: "Show:"
                        color: theme.subtext
                        font.pixelSize: 12
                    }

                    ComboBox {
                        id: capCombo
                        model: root._capOptions
                        currentIndex: root._capIndex
                        implicitWidth: 72
                        implicitHeight: 34
                        font.pixelSize: 12
                        onCurrentIndexChanged: {
                            root._capIndex = currentIndex
                            controller.setResultCap(root._capOptions[currentIndex])
                        }
                        background: Rectangle {
                            color: theme.base
                            border.color: capCombo.activeFocus ? theme.amber : (capCombo.hovered ? theme.blue : theme.surface1)
                            border.width: capCombo.activeFocus ? 2 : 1
                            radius: 6
                        }
                        contentItem: Label {
                            text: capCombo.displayText
                            color: theme.text
                            font.pixelSize: 12
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 8
                        }
                        popup: Popup {
                            width: capCombo.width
                            padding: 4
                            background: Rectangle {
                                color: theme.mantle
                                border.color: theme.surface0
                                radius: 6
                            }
                            contentItem: ListView {
                                implicitHeight: contentHeight
                                model: capCombo.delegateModel
                                clip: true
                            }
                        }
                        Keys.onTabPressed: {
                            event.accepted = true
                            if (searchBtn.activeFocusOnTab) searchBtn.forceActiveFocus(Qt.TabFocusReason)
                            else _focusResults()
                        }
                        Keys.onRightPressed: {
                            event.accepted = true
                            if (searchBtn.activeFocusOnTab) searchBtn.forceActiveFocus(Qt.TabFocusReason)
                            else _focusResults()
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        id: searchBtn
                        height: 34
                        width: searchBtnLbl.contentWidth + 28
                        radius: 8
                        activeFocusOnTab: queryField.text.trim().length > 0
                        color: {
                            if (root._searchState === "searching") return theme.surface1
                            return searchBtnMouse.containsMouse ? theme.blue + "dd" : theme.blue
                        }
                        border.color: (searchBtnMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
                        border.width: activeFocus ? 2 : 1

                        Label {
                            id: searchBtnLbl
                            anchors.centerIn: parent
                            text: root._searchState === "searching" ? "✕  Cancel" : "🔍  Search"
                            color: theme.isDark ? "#1e1e2e" : "#ffffff"
                            font.pixelSize: 13
                            font.bold: true
                        }

                        MouseArea {
                            id: searchBtnMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (root._searchState === "searching") {
                                    controller.cancelSearch()
                                } else {
                                    _doSearch()
                                }
                            }
                        }
                        Keys.onReturnPressed: root._searchState === "searching" ? controller.cancelSearch() : _doSearch()
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Space) {
                                root._searchState === "searching" ? controller.cancelSearch() : _doSearch()
                                event.accepted = true
                            }
                        }
                        Keys.onTabPressed:   { event.accepted = true; _focusResults() }
                        Keys.onRightPressed: { event.accepted = true; _focusResults() }
                        Keys.onBacktabPressed: { event.accepted = true; capCombo.forceActiveFocus(Qt.BacktabFocusReason) }
                        Keys.onLeftPressed:    { event.accepted = true; capCombo.forceActiveFocus(Qt.BacktabFocusReason) }
                    }
                }

                // Loading indicator
                RowLayout {
                    visible: root._searchState === "searching"
                    Layout.fillWidth: true
                    spacing: 10

                    BusyIndicator {
                        running: root._searchState === "searching"
                        implicitWidth: 22
                        implicitHeight: 22
                    }

                    Label {
                        text: "Searching..."
                        color: theme.subtext
                        font.pixelSize: 13
                    }
                }

                Item { height: 2 }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme.surface0
        }

        // Results area
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            // Error state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                visible: root._searchState === "error"

                Label {
                    text: "⚠"
                    font.pixelSize: 32
                    color: theme.amber
                    Layout.alignment: Qt.AlignHCenter
                }
                Label {
                    text: root._errorMessage
                    color: theme.subtext
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    width: 280
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // Empty state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                visible: root._searchState === "empty"

                Label {
                    text: "🔍"
                    font.pixelSize: 32
                    Layout.alignment: Qt.AlignHCenter
                }
                Label {
                    text: "No feeds found.\nTry a broader search term."
                    color: theme.subtext
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // Idle state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                visible: root._searchState === "idle"

                Label {
                    text: "📡"
                    font.pixelSize: 32
                    Layout.alignment: Qt.AlignHCenter
                }
                Label {
                    text: "Enter a topic above to discover feeds."
                    color: theme.subtext
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            // Results list
            ColumnLayout {
                anchors.fill: parent
                spacing: 0
                visible: root._searchState === "results"

                // Results header
                Rectangle {
                    Layout.fillWidth: true
                    height: 36
                    color: theme.base

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8

                        Label {
                            text: "RESULTS"
                            font.pixelSize: 11
                            font.bold: true
                            font.letterSpacing: 1.2
                            color: theme.overlay
                            Layout.fillWidth: true
                        }

                        Rectangle {
                            id: subSelBtn
                            visible: root.selectedCount > 0
                            height: 26
                            width: subSelLbl.contentWidth + 16
                            radius: 5
                            activeFocusOnTab: true
                            color: subSelMouse.containsMouse ? theme.surface0 : "transparent"
                            border.color: (subSelBtn.activeFocus || subSelMouse.containsMouse) ? theme.amber : theme.green
                            border.width: subSelBtn.activeFocus ? 2 : 1

                            Label {
                                id: subSelLbl
                                anchors.centerIn: parent
                                text: "Subscribe " + root.selectedCount
                                color: theme.green
                                font.pixelSize: 11
                                font.bold: true
                            }
                            MouseArea {
                                id: subSelMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: bulkConfirmDialog.open()
                            }
                            Keys.onReturnPressed: bulkConfirmDialog.open()
                            Keys.onPressed: function(event) {
                                if (event.key === Qt.Key_Space) { bulkConfirmDialog.open(); event.accepted = true }
                            }
                            Keys.onTabPressed:     { event.accepted = true; resultsList.forceActiveFocus(Qt.TabFocusReason) }
                            Keys.onRightPressed:   { event.accepted = true; resultsList.forceActiveFocus(Qt.TabFocusReason) }
                            Keys.onBacktabPressed: { event.accepted = true; _focusBeforeResults() }
                            Keys.onLeftPressed:    { event.accepted = true; _focusBeforeResults() }
                        }
                    }
                }

                ListView {
                    id: resultsList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    model: controller ? controller.candidateModel : null
                    ScrollBar.vertical: ScrollBar { id: resultsVScroll; policy: ScrollBar.AlwaysOn }

                    delegate: CandidateRow {
                        width: resultsList.width - resultsVScroll.width
                        theme: root.theme
                        selected: !!root.selectedUrls[candidateUrl]
                        onToggleRequested: root._toggleUrl(candidateUrl)
                        onSubscribeRequested: {
                            controller.subscribeFromDiscovery(candidateUrl)
                            root._showSingleToast(candidateTitle || candidateUrl)
                        }
                    }

                    Keys.onSpacePressed: function(event) {
                        if (currentIndex >= 0 && currentItem && !currentItem.candidateIsSubscribed) {
                            root._toggleUrl(currentItem.candidateUrl)
                            event.accepted = true
                        }
                    }
                    Keys.onReturnPressed: function(event) {
                        if (currentIndex >= 0 && currentItem && !currentItem.candidateIsSubscribed) {
                            controller.subscribeFromDiscovery(currentItem.candidateUrl)
                            _showSingleToast(currentItem.candidateTitle || currentItem.candidateUrl)
                            event.accepted = true
                        }
                    }
                    Keys.onTabPressed:     { event.accepted = true; queryField.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onRightPressed:   { event.accepted = true; queryField.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onBacktabPressed: { event.accepted = true; if (subSelBtn.visible) subSelBtn.forceActiveFocus(Qt.BacktabFocusReason); else _focusBeforeResults() }
                    Keys.onLeftPressed:    { event.accepted = true; if (subSelBtn.visible) subSelBtn.forceActiveFocus(Qt.BacktabFocusReason); else _focusBeforeResults() }

                    footer: Rectangle {
                        width: resultsList.width
                        height: visible ? 48 : 0
                        visible: root._hasMore
                        color: "transparent"

                        Rectangle {
                            anchors.centerIn: parent
                            width: moreLbl.contentWidth + 24
                            height: 32
                            radius: 6
                            color: moreMouse.containsMouse ? theme.surface0 : "transparent"
                            border.color: theme.blue
                            border.width: 1

                            Label {
                                id: moreLbl
                                anchors.centerIn: parent
                                text: "More results"
                                color: theme.blue
                                font.pixelSize: 12
                            }
                            MouseArea {
                                id: moreMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: { /* pagination TBD */ }
                            }
                        }
                    }
                }
            }
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

    Timer {
        id: autocompleteDebounce
        interval: 250
        repeat: false
        onTriggered: root._fetchSuggestions(queryField.text.trim())
    }

    function _fetchSuggestions(query) {
        if (root._currentXhr) {
            root._currentXhr.abort()
            root._currentXhr = null
        }
        if (query.length < 2) {
            root._suggestions = []
            autocompletePopup.close()
            return
        }
        var xhr = new XMLHttpRequest()
        root._currentXhr = xhr
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            root._currentXhr = null
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText)
                    root._suggestions = data[1] || []
                } catch(e) {
                    root._suggestions = []
                }
            } else {
                root._suggestions = []
            }
            if (root._suggestions.length > 0 && queryField.activeFocus) {
                autocompletePopup.open()
            } else {
                autocompletePopup.close()
            }
        }
        var url = "https://en.wikipedia.org/w/api.php?action=opensearch&search="
                  + encodeURIComponent(query)
                  + "&limit=10&format=json&namespace=0"
        xhr.open("GET", url)
        xhr.send()
    }

    function focusSearch() { queryField.forceActiveFocus() }
    function _focusResults() {
        if (root._searchState !== "results") return
        if (subSelBtn.visible) subSelBtn.forceActiveFocus(Qt.TabFocusReason)
        else resultsList.forceActiveFocus(Qt.TabFocusReason)
    }
    function _focusBeforeResults() {
        if (searchBtn.activeFocusOnTab) searchBtn.forceActiveFocus(Qt.BacktabFocusReason)
        else capCombo.forceActiveFocus(Qt.BacktabFocusReason)
    }

    function _doSearch() {
        var q = queryField.text.trim()
        if (q.length === 0) return
        autocompletePopup.close()
        root._clearSelection()
        controller.searchFeeds(q)
    }

    function _showSingleToast(title) {
        toastBar.show("Subscribed to " + title)
    }
}
