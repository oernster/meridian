import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The feed sidebar: select-all, the bulk remove button, the sort chips and the
// feed list itself.
//
// Extracted from main.qml. The selection lives with the window, because the
// context menu and the removal confirmations need it too, so it arrives here
// as a property and every change leaves as a signal.
//
// The sort chips are the awkward part of the focus ring: the active one is not
// a tab stop, so every neighbour has to search past it. That search was written
// out six times in the original. It is two functions here; everything that
// steps into or out of the chips goes through them.
Rectangle {
    id: sidebar

    required property var theme
    required property var feedModel
    required property var selectedFeedIds
    required property int selectedCount

    signal toggleRequested(int feedId)
    signal selectAllRequested()
    signal clearSelectionRequested()
    signal removeSelectedRequested()
    signal sortChosen(string key)
    signal feedActivated(int feedId)
    signal contextMenuRequested(int feedId, string title, real globalX, real globalY)
    signal focusBackwardRequested()

    property string _feedSort: "alpha_asc"

    readonly property var _sortOptions: [
        { key: "alpha_asc",  label: "A→Z"    },
        { key: "alpha_desc", label: "Z→A"    },
        { key: "unread",     label: "Unread" }
    ]

    function focusFirst() {
        checkAll.forceActiveFocus(Qt.TabFocusReason)
    }

    // The chip row answers whether a chip took focus, because every chip being
    // the active one is possible and there is somewhere else to go then.
    function _forwardPastChips() {
        if (!sortChips.focusFirst()) feedList.forceActiveFocus(Qt.TabFocusReason)
    }

    function _focusBeforeChips() {
        if (removeBtn.visible) removeBtn.forceActiveFocus(Qt.BacktabFocusReason)
        else checkAll.forceActiveFocus(Qt.BacktabFocusReason)
    }

    function _backwardFromList() {
        if (!sortChips.focusLast()) sidebar._focusBeforeChips()
    }

    function _toggleAll() {
        if (sidebar.selectedCount === feedList.count) sidebar.clearSelectionRequested()
        else sidebar.selectAllRequested()
    }

    color: theme.base

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            height: 38
            color: "transparent"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 8
                spacing: 6

                Rectangle {
                    id: checkAll
                    objectName: "checkAll"
                    width: 18; height: 18; radius: 3
                    activeFocusOnTab: true
                    color: sidebar.selectedCount > 0 ? theme.blue : "transparent"
                    border.color: activeFocus ? theme.amber : theme.blue
                    border.width: 2
                    Label {
                        anchors.centerIn: parent
                        text: sidebar.selectedCount === 0 ? ""
                            : sidebar.selectedCount === feedList.count ? "✓" : "–"
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 12; font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sidebar._toggleAll()
                    }
                    Keys.onReturnPressed: sidebar._toggleAll()
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Space) {
                            sidebar._toggleAll()
                            event.accepted = true
                        }
                    }
                    Keys.onTabPressed: {
                        event.accepted = true
                        if (removeBtn.visible) removeBtn.forceActiveFocus(Qt.TabFocusReason)
                        else sidebar._forwardPastChips()
                    }
                    Keys.onRightPressed: {
                        event.accepted = true
                        if (removeBtn.visible) removeBtn.forceActiveFocus(Qt.TabFocusReason)
                        else sidebar._forwardPastChips()
                    }
                    Keys.onBacktabPressed: { event.accepted = true; sidebar.focusBackwardRequested() }
                    Keys.onLeftPressed:    { event.accepted = true; sidebar.focusBackwardRequested() }
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
                    id: removeBtn
                    objectName: "removeBtn"
                    visible: sidebar.selectedCount > 0
                    height: 24
                    width: removeLbl.contentWidth + 14
                    radius: 4
                    activeFocusOnTab: visible
                    color: removeMouse.containsMouse ? theme.surface0 : "transparent"
                    border.color: theme.red
                    border.width: activeFocus ? 2 : 1
                    Label {
                        id: removeLbl
                        anchors.centerIn: parent
                        text: "Remove " + sidebar.selectedCount
                        color: theme.red
                        font.pixelSize: 10; font.bold: true
                    }
                    MouseArea {
                        id: removeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: sidebar.removeSelectedRequested()
                    }
                    Keys.onReturnPressed: sidebar.removeSelectedRequested()
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Space) {
                            sidebar.removeSelectedRequested()
                            event.accepted = true
                        }
                    }
                    Keys.onTabPressed:     { event.accepted = true; sidebar._forwardPastChips() }
                    Keys.onRightPressed:   { event.accepted = true; sidebar._forwardPastChips() }
                    Keys.onBacktabPressed: { event.accepted = true; checkAll.forceActiveFocus(Qt.BacktabFocusReason) }
                    Keys.onLeftPressed:    { event.accepted = true; checkAll.forceActiveFocus(Qt.BacktabFocusReason) }
                }

                SortChipRow {
                    id: sortChips
                    theme: sidebar.theme
                    options: sidebar._sortOptions
                    current: sidebar._feedSort
                    onChosen: function(key) {
                        sidebar._feedSort = key
                        sidebar.sortChosen(key)
                    }
                    onForwardOverflow: feedList.forceActiveFocus(Qt.TabFocusReason)
                    onBackwardOverflow: sidebar._focusBeforeChips()
                }
            }
        }

        ListView {
            id: feedList
            objectName: "feedList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: sidebar.feedModel
            currentIndex: -1
            activeFocusOnTab: true
            keyNavigationEnabled: true
            ScrollBar.vertical: ScrollBar { id: vScroll; policy: ScrollBar.AlwaysOn }

            delegate: FeedRow {
                width: feedList.width - vScroll.width
                theme: sidebar.theme
                selected: !!sidebar.selectedFeedIds[feedId]
                onToggleRequested: sidebar.toggleRequested(feedId)
                onActivated: {
                    feedList.currentIndex = index
                    sidebar.feedActivated(feedId)
                    feedList.forceActiveFocus(Qt.MouseFocusReason)
                }
                onContextMenuRequested: function(globalX, globalY) {
                    sidebar.contextMenuRequested(
                        feedId, feedTitle || feedUrl, globalX, globalY
                    )
                }
            }

            onActiveFocusChanged: {
                if (activeFocus && currentIndex < 0 && count > 0) currentIndex = 0
            }
            onCurrentIndexChanged: {
                if (activeFocus && currentIndex >= 0) sidebar.feedActivated(_currentFeedId())
            }

            function _currentFeedId() {
                return sidebar.feedModel.data(
                    sidebar.feedModel.index(feedList.currentIndex, 0), Qt.UserRole
                )
            }

            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Space && currentIndex >= 0) {
                    sidebar.toggleRequested(feedList._currentFeedId())
                    event.accepted = true
                }
            }
            Keys.onRightPressed: {
                event.accepted = true
                var next = feedList.nextItemInFocusChain(true)
                if (next && next !== feedList) next.forceActiveFocus(Qt.TabFocusReason)
            }
            Keys.onBacktabPressed: { event.accepted = true; sidebar._backwardFromList() }
            Keys.onLeftPressed:    { event.accepted = true; sidebar._backwardFromList() }
        }
    }
}
