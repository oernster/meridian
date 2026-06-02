import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    title: "Meridian"
    width: 1280
    height: 800
    minimumWidth: 920
    minimumHeight: 580
    visible: true

    // ── Theme (Catppuccin Mocha / Latte) ──────────────────────────────
    QtObject {
        id: theme
        property bool isDark: true

        // Catppuccin Mocha (dark)
        readonly property color _dCrust:    "#11111b"
        readonly property color _dMantle:   "#181825"
        readonly property color _dBase:     "#1e1e2e"
        readonly property color _dSurface0: "#313244"
        readonly property color _dSurface1: "#45475a"
        readonly property color _dOverlay:  "#6c7086"
        readonly property color _dSubtext:  "#a6adc8"
        readonly property color _dText:     "#cdd6f4"
        readonly property color _dBlue:     "#89b4fa"
        readonly property color _dRed:      "#f38ba8"
        readonly property color _dGreen:    "#a6e3a1"

        // Catppuccin Latte (light)
        readonly property color _lCrust:    "#dce0e8"
        readonly property color _lMantle:   "#e6e9ef"
        readonly property color _lBase:     "#eff1f5"
        readonly property color _lSurface0: "#ccd0da"
        readonly property color _lSurface1: "#bcc0cc"
        readonly property color _lOverlay:  "#9ca0b0"
        readonly property color _lSubtext:  "#6c6f85"
        readonly property color _lText:     "#4c4f69"
        readonly property color _lBlue:     "#1e66f5"
        readonly property color _lRed:      "#d20f39"
        readonly property color _lGreen:    "#40a02b"

        property color crust:    isDark ? _dCrust    : _lCrust
        property color mantle:   isDark ? _dMantle   : _lMantle
        property color base:     isDark ? _dBase     : _lBase
        property color surface0: isDark ? _dSurface0 : _lSurface0
        property color surface1: isDark ? _dSurface1 : _lSurface1
        property color overlay:  isDark ? _dOverlay  : _lOverlay
        property color subtext:  isDark ? _dSubtext  : _lSubtext
        property color text:     isDark ? _dText      : _lText
        property color blue:     isDark ? _dBlue     : _lBlue
        property color red:      isDark ? _dRed      : _lRed
        property color green:    isDark ? _dGreen    : _lGreen
        property color amber:    isDark ? "#fab387"  : "#e67e22"
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
            var id = m.data(m.index(i, 0), Qt.UserRole)
            s[id] = true
        }
        _selectedFeedIds = s
        _selectedFeedCount = Object.keys(s).length
    }
    function _clearFeedSelection() { _selectedFeedIds = {}; _selectedFeedCount = 0 }

    menuBar: MenuBar {
        id: appMenuBar
        activeFocusOnTab: true

        delegate: MenuBarItem {
            id: menuBarDelegate

            contentItem: Text {
                text: menuBarDelegate.text.replace("&", "")
                color: theme.text
                font: menuBarDelegate.font
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }

            background: Rectangle {
                color: menuBarDelegate.highlighted ? theme.surface0 : "transparent"
                border.color: menuBarDelegate.activeFocus ? theme.amber : "transparent"
                border.width: 1
                radius: 4
            }

            function navigateNext() {
                for (var i = 0; i < appMenuBar.count; i++) {
                    if (appMenuBar.itemAt(i) === menuBarDelegate) {
                        var next = i + 1
                        if (next < appMenuBar.count)
                            appMenuBar.itemAt(next).forceActiveFocus(Qt.TabFocusReason)
                        else
                            discoverBtn.forceActiveFocus(Qt.TabFocusReason)
                        return
                    }
                }
            }

            function navigatePrev() {
                for (var i = 0; i < appMenuBar.count; i++) {
                    if (appMenuBar.itemAt(i) === menuBarDelegate) {
                        var prev = i - 1
                        if (prev >= 0)
                            appMenuBar.itemAt(prev).forceActiveFocus(Qt.BacktabFocusReason)
                        else
                            initialFocusItem.forceActiveFocus(Qt.BacktabFocusReason)
                        return
                    }
                }
            }

            Keys.onTabPressed:     { event.accepted = true; navigateNext() }
            Keys.onBacktabPressed: { event.accepted = true; navigatePrev() }
            Keys.onRightPressed:   { event.accepted = true; navigateNext() }
            Keys.onLeftPressed:    { event.accepted = true; navigatePrev() }
            Keys.onDownPressed:    { event.accepted = true; menuBarDelegate.menu.open(); Qt.callLater(function() { menuBarDelegate.menu.currentIndex = 0 }) }
            Keys.onReturnPressed:  { event.accepted = true; menuBarDelegate.menu.open(); Qt.callLater(function() { menuBarDelegate.menu.currentIndex = 0 }) }
            Keys.onSpacePressed:   { event.accepted = true; menuBarDelegate.menu.open(); Qt.callLater(function() { menuBarDelegate.menu.currentIndex = 0 }) }
        }

        Menu {
            id: fileMenu
            title: "&File"
            MenuItem {
                text: "Import Feeds..."
                onTriggered: importDialog.open()
                Keys.onTabPressed:     { event.accepted = true; fileMenu.close(); appMenuBar.itemAt(1).forceActiveFocus(Qt.TabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; fileMenu.close(); appMenuBar.itemAt(1).forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; fileMenu.close(); initialFocusItem.forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; fileMenu.close(); initialFocusItem.forceActiveFocus(Qt.BacktabFocusReason) }
            }
            MenuItem {
                text: "Export Feeds..."
                onTriggered: exportDialog.open()
                Keys.onTabPressed:     { event.accepted = true; fileMenu.close(); appMenuBar.itemAt(1).forceActiveFocus(Qt.TabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; fileMenu.close(); appMenuBar.itemAt(1).forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; fileMenu.close(); initialFocusItem.forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; fileMenu.close(); initialFocusItem.forceActiveFocus(Qt.BacktabFocusReason) }
            }
        }
        Menu {
            id: helpMenu
            title: "&Help"
            MenuItem {
                text: "About Meridian"
                onTriggered: aboutDialog.open()
                Keys.onTabPressed:     { event.accepted = true; helpMenu.close(); discoverBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; helpMenu.close(); discoverBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; helpMenu.close(); appMenuBar.itemAt(0).forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; helpMenu.close(); appMenuBar.itemAt(0).forceActiveFocus(Qt.BacktabFocusReason) }
            }
            MenuItem {
                text: "Licence"
                onTriggered: licenceDialog.open()
                Keys.onTabPressed:     { event.accepted = true; helpMenu.close(); discoverBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; helpMenu.close(); discoverBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; helpMenu.close(); appMenuBar.itemAt(0).forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; helpMenu.close(); appMenuBar.itemAt(0).forceActiveFocus(Qt.BacktabFocusReason) }
            }
        }
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
    // First Tab press explicitly navigates to the File menu.
    Item {
        id: initialFocusItem
        focus: true
        activeFocusOnTab: false
        width: 0; height: 0
        Keys.onTabPressed: {
            event.accepted = true
            if (appMenuBar.count > 0)
                appMenuBar.itemAt(0).forceActiveFocus(Qt.TabFocusReason)
        }
    }

    // ── Layout ────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header bar
        Rectangle {
            Layout.fillWidth: true
            height: 52
            color: theme.mantle

            Image {
                id: headerIcon
                source: appIconUrl
                width: 28; height: 28
                fillMode: Image.PreserveAspectFit
                visible: appIconUrl !== ""
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
            }

            Label {
                text: "Meridian"
                font.pixelSize: 18
                font.bold: true
                color: theme.text
                font.letterSpacing: 0.4
                anchors.left: headerIcon.visible ? headerIcon.right : parent.left
                anchors.leftMargin: headerIcon.visible ? 8 : 14
                anchors.verticalCenter: parent.verticalCenter
            }

            // Discover Feeds
            Rectangle {
                id: discoverBtn
                width: discoverLbl.contentWidth + 24; height: 34; radius: 8
                anchors.right: manageBtn.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                activeFocusOnTab: true
                color: discoverHeaderMouse.containsMouse ? theme.surface0 : theme.surface1
                border.color: (discoverHeaderMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
                border.width: 1
                Label {
                    id: discoverLbl
                    anchors.centerIn: parent
                    text: "🔍  Search"
                    font.pixelSize: 13
                    color: theme.text
                }
                MouseArea {
                    id: discoverHeaderMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: feedDiscoveryDrawer.open()
                }
                Keys.onReturnPressed: feedDiscoveryDrawer.open()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space) { feedDiscoveryDrawer.open(); event.accepted = true }
                }
                Keys.onTabPressed:     { event.accepted = true; manageBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; appMenuBar.itemAt(appMenuBar.count - 1).forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; manageBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; appMenuBar.itemAt(appMenuBar.count - 1).forceActiveFocus(Qt.BacktabFocusReason) }
            }

            // Manage Subscriptions
            Rectangle {
                id: manageBtn
                width: manageLbl.contentWidth + 24; height: 34; radius: 8
                anchors.right: themeToggleBtn.left
                anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                activeFocusOnTab: true
                color: manageHeaderMouse.containsMouse ? theme.surface0 : theme.surface1
                border.color: (manageHeaderMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
                border.width: 1
                Label {
                    id: manageLbl
                    anchors.centerIn: parent
                    text: "⚙  Manage"
                    font.pixelSize: 13
                    color: theme.text
                }
                MouseArea {
                    id: manageHeaderMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: subManagerDrawer.open()
                }
                Keys.onReturnPressed: subManagerDrawer.open()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space) { subManagerDrawer.open(); event.accepted = true }
                }
                Keys.onTabPressed:     { event.accepted = true; themeToggleBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; discoverBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; themeToggleBtn.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; discoverBtn.forceActiveFocus(Qt.BacktabFocusReason) }
            }

            // Theme toggle
            Rectangle {
                id: themeToggleBtn
                width: 40; height: 34; radius: 6
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                activeFocusOnTab: true
                color: themeToggleMouse.containsMouse ? theme.surface0 : "transparent"
                border.color: (themeToggleMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
                border.width: 1
                Label {
                    anchors.centerIn: parent
                    text: theme.isDark ? "☀️" : "🌙"
                    font.pixelSize: 16
                    color: theme.text
                }
                MouseArea {
                    id: themeToggleMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: theme.isDark = !theme.isDark
                }
                Keys.onReturnPressed: theme.isDark = !theme.isDark
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space) { theme.isDark = !theme.isDark; event.accepted = true }
                }
                Keys.onTabPressed:     { event.accepted = true; feedCheckAll.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; manageBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; feedCheckAll.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; manageBtn.forceActiveFocus(Qt.BacktabFocusReason) }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.surface0
            }
        }

        // Main content: sidebar + reader
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            // Sidebar
            Rectangle {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                color: theme.base

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Rectangle {
                        id: feedsHeader
                        Layout.fillWidth: true
                        height: 38
                        color: "transparent"

                        property string _feedSort: "alpha_asc"

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 8
                            anchors.rightMargin: 8
                            spacing: 6

                            Rectangle {
                                id: feedCheckAll
                                width: 18; height: 18; radius: 3
                                activeFocusOnTab: true
                                color: root._selectedFeedCount > 0 ? theme.blue : "transparent"
                                border.color: activeFocus ? theme.amber : theme.blue
                                border.width: activeFocus ? 2 : 2
                                Label {
                                    anchors.centerIn: parent
                                    text: root._selectedFeedCount > 0 && root._selectedFeedCount === controller.feedModel.rowCount() ? "✓" : (root._selectedFeedCount > 0 ? "–" : "")
                                    color: theme.isDark ? "#1e1e2e" : "#ffffff"
                                    font.pixelSize: 12; font.bold: true
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root._selectedFeedCount === controller.feedModel.rowCount() ? root._clearFeedSelection() : root._selectAllFeeds()
                                }
                                Keys.onReturnPressed: root._selectedFeedCount === controller.feedModel.rowCount() ? root._clearFeedSelection() : root._selectAllFeeds()
                                Keys.onPressed: function(event) {
                                    if (event.key === Qt.Key_Space) {
                                        root._selectedFeedCount === controller.feedModel.rowCount() ? root._clearFeedSelection() : root._selectAllFeeds()
                                        event.accepted = true
                                    }
                                }
                                Keys.onTabPressed: {
                                    event.accepted = true
                                    if (removeFeedsBtn.visible) { removeFeedsBtn.forceActiveFocus(Qt.TabFocusReason); return }
                                    var found = false
                                    for (var i = 0; i < sortRepeater.count; i++) {
                                        var it = sortRepeater.itemAt(i)
                                        if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                    }
                                    if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                }
                                Keys.onBacktabPressed: { event.accepted = true; themeToggleBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                                Keys.onRightPressed: {
                                    event.accepted = true
                                    if (removeFeedsBtn.visible) { removeFeedsBtn.forceActiveFocus(Qt.TabFocusReason); return }
                                    var found = false
                                    for (var i = 0; i < sortRepeater.count; i++) {
                                        var it = sortRepeater.itemAt(i)
                                        if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                    }
                                    if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                }
                                Keys.onLeftPressed:    { event.accepted = true; themeToggleBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                            }

                            Label {
                                text: "FEEDS"
                                font.pixelSize: 11
                                font.bold: true
                                font.letterSpacing: 1.4
                                color: theme.overlay
                                Layout.fillWidth: true
                            }

                            Rectangle {
                                id: removeFeedsBtn
                                visible: root._selectedFeedCount > 0
                                height: 24
                                width: _removeFeedsLbl.contentWidth + 14
                                radius: 4
                                activeFocusOnTab: visible
                                color: _removeFeedsMouse.containsMouse ? theme.surface0 : "transparent"
                                border.color: (_removeFeedsMouse.containsMouse || activeFocus) ? theme.red : theme.red
                                border.width: activeFocus ? 2 : 1
                                Label {
                                    id: _removeFeedsLbl
                                    anchors.centerIn: parent
                                    text: "Remove " + root._selectedFeedCount
                                    color: theme.red
                                    font.pixelSize: 10; font.bold: true
                                }
                                MouseArea {
                                    id: _removeFeedsMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        feedBulkDeleteDialog.pendingBulkIds = Object.keys(root._selectedFeedIds).map(function(k) { return parseInt(k) })
                                        feedBulkDeleteDialog.open()
                                    }
                                }
                                Keys.onReturnPressed: {
                                    feedBulkDeleteDialog.pendingBulkIds = Object.keys(root._selectedFeedIds).map(function(k) { return parseInt(k) })
                                    feedBulkDeleteDialog.open()
                                }
                                Keys.onPressed: function(event) {
                                    if (event.key === Qt.Key_Space) {
                                        feedBulkDeleteDialog.pendingBulkIds = Object.keys(root._selectedFeedIds).map(function(k) { return parseInt(k) })
                                        feedBulkDeleteDialog.open()
                                        event.accepted = true
                                    }
                                }
                                Keys.onTabPressed: {
                                    event.accepted = true
                                    var found = false
                                    for (var i = 0; i < sortRepeater.count; i++) {
                                        var it = sortRepeater.itemAt(i)
                                        if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                    }
                                    if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                }
                                Keys.onRightPressed: {
                                    event.accepted = true
                                    var found = false
                                    for (var i = 0; i < sortRepeater.count; i++) {
                                        var it = sortRepeater.itemAt(i)
                                        if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                    }
                                    if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                }
                                Keys.onBacktabPressed: { event.accepted = true; feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason) }
                                Keys.onLeftPressed:    { event.accepted = true; feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason) }
                            }

                            Row {
                                spacing: 4
                                Repeater {
                                    id: sortRepeater
                                    model: [
                                        { key: "alpha_asc",  label: "A→Z"    },
                                        { key: "alpha_desc", label: "Z→A"    },
                                        { key: "unread",     label: "Unread" }
                                    ]
                                    delegate: Rectangle {
                                        property bool isActive: feedsHeader._feedSort === modelData.key
                                        property bool _hov: false
                                        height: 24; radius: 4
                                        implicitWidth: _sl.implicitWidth + 12
                                        activeFocusOnTab: !isActive
                                        color: isActive ? theme.surface0 : "transparent"
                                        border.color: isActive ? theme.blue : (_hov || activeFocus) ? theme.amber : "transparent"
                                        border.width: activeFocus ? 2 : 1
                                        Label {
                                            id: _sl
                                            anchors.centerIn: parent
                                            text: modelData.label
                                            color: parent.isActive ? theme.blue : (parent._hov || parent.activeFocus) ? theme.text : theme.overlay
                                            font.pixelSize: 10; font.bold: parent.isActive
                                        }
                                        HoverHandler { onHoveredChanged: parent._hov = hovered }
                                        MouseArea {
                                            anchors.fill: parent
                                            enabled: !parent.isActive
                                            cursorShape: parent.isActive ? Qt.ArrowCursor : Qt.PointingHandCursor
                                            onClicked: {
                                                feedsHeader._feedSort = modelData.key
                                                controller.setFeedSort(modelData.key)
                                            }
                                        }
                                        Keys.onReturnPressed: { if (!isActive) { feedsHeader._feedSort = modelData.key; controller.setFeedSort(modelData.key) } }
                                        Keys.onPressed: function(event) {
                                            if (event.key === Qt.Key_Space && !isActive) {
                                                feedsHeader._feedSort = modelData.key
                                                controller.setFeedSort(modelData.key)
                                                event.accepted = true
                                            }
                                        }
                                        Keys.onTabPressed: {
                                            event.accepted = true
                                            var found = false
                                            for (var i = index + 1; i < sortRepeater.count; i++) {
                                                var it = sortRepeater.itemAt(i)
                                                if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                            }
                                            if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                        }
                                        Keys.onBacktabPressed: {
                                            event.accepted = true
                                            var found = false
                                            for (var i = index - 1; i >= 0; i--) {
                                                var it = sortRepeater.itemAt(i)
                                                if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                            }
                                            if (!found) {
                                                if (removeFeedsBtn.visible) removeFeedsBtn.forceActiveFocus(Qt.BacktabFocusReason)
                                                else feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason)
                                            }
                                        }
                                        Keys.onRightPressed: {
                                            event.accepted = true
                                            var found = false
                                            for (var i = index + 1; i < sortRepeater.count; i++) {
                                                var it = sortRepeater.itemAt(i)
                                                if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                            }
                                            if (!found) feedList.forceActiveFocus(Qt.TabFocusReason)
                                        }
                                        Keys.onLeftPressed: {
                                            event.accepted = true
                                            var found = false
                                            for (var i = index - 1; i >= 0; i--) {
                                                var it = sortRepeater.itemAt(i)
                                                if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                            }
                                            if (!found) {
                                                if (removeFeedsBtn.visible) removeFeedsBtn.forceActiveFocus(Qt.BacktabFocusReason)
                                                else feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    ListView {
                        id: feedList
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: controller.feedModel
                        delegate: feedDelegate
                        currentIndex: -1
                        activeFocusOnTab: true
                        keyNavigationEnabled: true
                        ScrollBar.vertical: ScrollBar { id: feedVScroll; policy: ScrollBar.AlwaysOn }
                        onActiveFocusChanged: {
                            if (activeFocus && currentIndex < 0 && count > 0)
                                currentIndex = 0
                        }
                        onCurrentIndexChanged: {
                            if (activeFocus && currentIndex >= 0) {
                                var feedId = controller.feedModel.data(
                                    controller.feedModel.index(currentIndex, 0), Qt.UserRole)
                                controller.selectFeed(feedId)
                            }
                        }
                        Keys.onPressed: function(event) {
                            if (event.key === Qt.Key_Space && currentIndex >= 0) {
                                var feedId = controller.feedModel.data(
                                    controller.feedModel.index(currentIndex, 0), Qt.UserRole)
                                root._toggleFeed(feedId)
                                event.accepted = true
                            }
                        }
                        Keys.onRightPressed: {
                            event.accepted = true
                            var next = feedList.nextItemInFocusChain(true)
                            if (next && next !== feedList) next.forceActiveFocus(Qt.TabFocusReason)
                        }
                        Keys.onBacktabPressed: {
                            event.accepted = true
                            var found = false
                            for (var i = sortRepeater.count - 1; i >= 0; i--) {
                                var it = sortRepeater.itemAt(i)
                                if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                            }
                            if (!found) feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason)
                        }
                        Keys.onLeftPressed: {
                            event.accepted = true
                            var found = false
                            for (var i = sortRepeater.count - 1; i >= 0; i--) {
                                var it = sortRepeater.itemAt(i)
                                if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                            }
                            if (!found) feedCheckAll.forceActiveFocus(Qt.BacktabFocusReason)
                        }
                    }


                }
            }

            // Divider
            Rectangle {
                width: 1
                Layout.fillHeight: true
                color: theme.surface0
            }

            FeedReader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                theme: theme
            }
        }
    }

    // ── Feed delegate ─────────────────────────────────────────────────
    Component {
        id: feedDelegate

        Rectangle {
            id: feedRow
            width: feedList.width - feedVScroll.width
            height: 64
            color: feedList.currentIndex === index ? theme.surface0 : "transparent"
            border.color: (feedRowMouse.containsMouse || ListView.isCurrentItem) ? theme.amber : "transparent"
            border.width: 1

            MouseArea {
                id: feedRowMouse
                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton | Qt.RightButton
                onPressed: function(mouse) {
                    if (mouse.button === Qt.RightButton) {
                        mouse.accepted = true
                        var gp = feedRow.mapToGlobal(mouse.x, mouse.y)
                        var op = Overlay.overlay.mapFromGlobal(gp.x, gp.y)
                        feedContextPopup.targetFeedId = model.feedId
                        feedContextPopup.targetTitle  = model.feedTitle || model.feedUrl
                        feedContextPopup.x = op.x
                        feedContextPopup.y = op.y
                        feedContextPopup.open()
                    }
                }
                onClicked: function(mouse) {
                    if (mouse.button === Qt.LeftButton) {
                        feedList.currentIndex = index
                        controller.selectFeed(model.feedId)
                    }
                }
            }

            Rectangle {
                visible: feedList.currentIndex === index
                width: 3; height: 40; radius: 2
                color: theme.blue
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8; anchors.rightMargin: 12
                anchors.topMargin: 8; anchors.bottomMargin: 8
                spacing: 8
                z: 1

                Rectangle {
                    width: 22; height: 22; radius: 3
                    color: !!root._selectedFeedIds[model.feedId] ? theme.blue : "transparent"
                    border.color: theme.blue; border.width: 2
                    Label {
                        anchors.centerIn: parent
                        text: !!root._selectedFeedIds[model.feedId] ? "✓" : ""
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 12; font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        anchors.margins: -4
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root._toggleFeed(model.feedId)
                    }
                }

                Item {
                    Layout.preferredWidth: 36
                    Layout.preferredHeight: 36
                    Layout.minimumWidth: 36
                    Layout.minimumHeight: 36
                    Layout.maximumWidth: 36
                    Layout.maximumHeight: 36

                    Rectangle {
                        width: 36; height: 36; radius: 8
                        color: theme.surface0
                        visible: model.feedIcon === ""
                        Label {
                            anchors.centerIn: parent
                            text: (model.feedTitle || model.feedUrl).charAt(0).toUpperCase()
                            color: theme.blue; font.pixelSize: 15; font.bold: true
                        }
                    }
                    Image {
                        width: 36; height: 36
                        source: model.feedIcon
                        sourceSize: Qt.size(36, 36)
                        fillMode: Image.PreserveAspectFit
                        visible: model.feedIcon !== ""
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Label {
                        text: model.feedTitle || model.feedUrl
                        color: theme.text; font.pixelSize: 13
                        elide: Text.ElideRight; Layout.fillWidth: true
                    }
                    Label {
                        text: model.feedSourceType.toUpperCase()
                        color: theme.blue; font.pixelSize: 10; font.bold: true
                    }
                }

                Rectangle {
                    visible: model.feedUnreadCount > 0
                    width: Math.max(bdg.contentWidth + 14, 24); height: 22; radius: 11
                    color: theme.blue
                    Label {
                        id: bdg; anchors.centerIn: parent
                        text: model.feedUnreadCount > 99 ? "99+" : model.feedUnreadCount
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 11; font.bold: true
                    }
                }
            }
        }
    }

    Popup {
        id: feedContextPopup
        parent: Overlay.overlay
        property int targetFeedId: 0
        property string targetTitle: ""
        padding: 4
        width: 180
        height: root._selectedFeedCount > 0 ? 80 : 44
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: theme.mantle
            border.color: theme.surface0
            border.width: 1
            radius: 6
        }

        Column {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                width: parent.width; height: 36
                radius: 4
                color: ctxHover.containsMouse ? theme.surface0 : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Remove Feed"
                    color: theme.red
                    font.pixelSize: 13
                    font.bold: true
                }
                MouseArea {
                    id: ctxHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        feedContextPopup.close()
                        feedDeleteConfirmDialog.targetFeedId = feedContextPopup.targetFeedId
                        feedDeleteConfirmDialog.targetTitle  = feedContextPopup.targetTitle
                        feedDeleteConfirmDialog.open()
                    }
                }
            }

            Rectangle {
                visible: root._selectedFeedCount > 0
                width: parent.width; height: 36
                radius: 4
                color: ctxBulkHover.containsMouse ? theme.surface0 : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "Remove " + root._selectedFeedCount + " selected"
                    color: theme.red
                    font.pixelSize: 13
                    font.bold: true
                }
                MouseArea {
                    id: ctxBulkHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        feedBulkDeleteDialog.pendingBulkIds = Object.keys(root._selectedFeedIds).map(function(k) { return parseInt(k) })
                        feedContextPopup.close()
                        Qt.callLater(feedBulkDeleteDialog.open)
                    }
                }
            }
        }
    }

    Dialog {
        id: feedDeleteConfirmDialog
        property int targetFeedId: 0
        property string targetTitle: ""
        modal: true
        title: "Remove Feed"
        anchors.centerIn: Overlay.overlay
        background: Rectangle { color: theme.base; border.color: theme.surface0; radius: 8 }
        footer: Rectangle {
            color: theme.mantle
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                StyledButton {
                    id: deleteCancelBtn
                    text: "Cancel"; theme: theme; onClicked: feedDeleteConfirmDialog.reject()
                    Keys.onReturnPressed: { feedDeleteConfirmDialog.reject(); event.accepted = true }
                    Keys.onRightPressed: { deleteOkBtn.forceActiveFocus(); event.accepted = true }
                }
                StyledButton {
                    id: deleteOkBtn
                    text: "OK"; theme: theme; onClicked: feedDeleteConfirmDialog.accept()
                    Keys.onReturnPressed: { feedDeleteConfirmDialog.accept(); event.accepted = true }
                    Keys.onLeftPressed: { deleteCancelBtn.forceActiveFocus(); event.accepted = true }
                }
            }
        }
        Label {
            text: "Remove \"" + feedDeleteConfirmDialog.targetTitle + "\"?\nAll downloaded items will be deleted."
            wrapMode: Text.WordWrap; width: 320; color: theme.text; lineHeight: 1.4
        }
        onAccepted: controller.unsubscribe(feedDeleteConfirmDialog.targetFeedId)
    }

    Dialog {
        id: feedBulkDeleteDialog
        property var pendingBulkIds: []
        modal: true
        title: "Remove Feeds"
        anchors.centerIn: Overlay.overlay
        background: Rectangle { color: theme.base; border.color: theme.surface0; radius: 8 }
        footer: Rectangle {
            color: theme.mantle
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                StyledButton {
                    id: bulkDeleteCancelBtn
                    text: "Cancel"; theme: theme; onClicked: feedBulkDeleteDialog.reject()
                    Keys.onReturnPressed: { feedBulkDeleteDialog.reject(); event.accepted = true }
                    Keys.onRightPressed: { bulkDeleteOkBtn.forceActiveFocus(); event.accepted = true }
                }
                StyledButton {
                    id: bulkDeleteOkBtn
                    text: "OK"; theme: theme; onClicked: feedBulkDeleteDialog.accept()
                    Keys.onReturnPressed: { feedBulkDeleteDialog.accept(); event.accepted = true }
                    Keys.onLeftPressed: { bulkDeleteCancelBtn.forceActiveFocus(); event.accepted = true }
                }
            }
        }
        Label {
            text: "Remove " + feedBulkDeleteDialog.pendingBulkIds.length + " feed(s)?\nAll downloaded items will be deleted."
            wrapMode: Text.WordWrap; width: 320; color: theme.text; lineHeight: 1.4
        }
        onAccepted: {
            root._clearFeedSelection()
            controller.bulkUnsubscribe(feedBulkDeleteDialog.pendingBulkIds)
        }
    }

    // ── Drawers & dialogs ─────────────────────────────────────────────
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
        theme: theme
    }

    LicenceDialog {
        id: licenceDialog
        theme: theme
    }

    Dialog {
        id: errorDialog
        modal: true
        title: "Error"
        property string message: ""
        anchors.centerIn: Overlay.overlay

        background: Rectangle {
            color: theme.base
            border.color: theme.surface0
            radius: 8
        }

        footer: Rectangle {
            color: theme.mantle
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            StyledButton {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "OK"
                theme: theme
                onClicked: errorDialog.accept()
                Keys.onReturnPressed: { errorDialog.accept(); event.accepted = true }
            }
        }

        Label {
            text: errorDialog.message
            color: theme.text
            wrapMode: Text.WordWrap
            width: 320
        }
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
