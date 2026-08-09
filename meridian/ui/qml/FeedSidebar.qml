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

    // Both return whether they found a chip to land on, because the caller has
    // somewhere different to go when every chip is the active one.
    function _focusNextChipAfter(index) {
        for (var i = index + 1; i < sortRepeater.count; i++) {
            var chip = sortRepeater.itemAt(i)
            if (chip && !chip.isActive) {
                chip.forceActiveFocus(Qt.TabFocusReason)
                return true
            }
        }
        return false
    }

    function _focusPreviousChipBefore(index) {
        for (var i = index - 1; i >= 0; i--) {
            var chip = sortRepeater.itemAt(i)
            if (chip && !chip.isActive) {
                chip.forceActiveFocus(Qt.BacktabFocusReason)
                return true
            }
        }
        return false
    }

    function _forwardIntoChips(index) {
        if (!sidebar._focusNextChipAfter(index)) {
            feedList.forceActiveFocus(Qt.TabFocusReason)
        }
    }

    function _backwardOutOfChips(index) {
        if (sidebar._focusPreviousChipBefore(index)) return
        if (removeBtn.visible) removeBtn.forceActiveFocus(Qt.BacktabFocusReason)
        else checkAll.forceActiveFocus(Qt.BacktabFocusReason)
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
                        else sidebar._forwardIntoChips(-1)
                    }
                    Keys.onRightPressed: {
                        event.accepted = true
                        if (removeBtn.visible) removeBtn.forceActiveFocus(Qt.TabFocusReason)
                        else sidebar._forwardIntoChips(-1)
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
                    Keys.onTabPressed:     { event.accepted = true; sidebar._forwardIntoChips(-1) }
                    Keys.onRightPressed:   { event.accepted = true; sidebar._forwardIntoChips(-1) }
                    Keys.onBacktabPressed: { event.accepted = true; checkAll.forceActiveFocus(Qt.BacktabFocusReason) }
                    Keys.onLeftPressed:    { event.accepted = true; checkAll.forceActiveFocus(Qt.BacktabFocusReason) }
                }

                Row {
                    spacing: 4
                    Repeater {
                        id: sortRepeater
                        model: sidebar._sortOptions
                        delegate: Rectangle {
                            id: chip
                            objectName: "sortChip_" + modelData.key
                            property bool isActive: sidebar._feedSort === modelData.key
                            property bool hovered: false
                            height: 24; radius: 4
                            implicitWidth: chipLabel.implicitWidth + 12
                            activeFocusOnTab: !isActive
                            color: isActive ? theme.surface0 : "transparent"
                            border.color: isActive ? theme.blue
                                        : (hovered || activeFocus) ? theme.amber : "transparent"
                            border.width: activeFocus ? 2 : 1
                            Label {
                                id: chipLabel
                                anchors.centerIn: parent
                                text: modelData.label
                                color: chip.isActive ? theme.blue
                                     : (chip.hovered || chip.activeFocus) ? theme.text : theme.overlay
                                font.pixelSize: 10; font.bold: chip.isActive
                            }
                            HoverHandler { onHoveredChanged: chip.hovered = hovered }
                            MouseArea {
                                anchors.fill: parent
                                enabled: !chip.isActive
                                cursorShape: chip.isActive ? Qt.ArrowCursor : Qt.PointingHandCursor
                                onClicked: chip._choose()
                            }

                            function _choose() {
                                if (chip.isActive) return
                                sidebar._feedSort = modelData.key
                                sidebar.sortChosen(modelData.key)
                            }

                            Keys.onReturnPressed: chip._choose()
                            Keys.onPressed: function(event) {
                                if (event.key === Qt.Key_Space) {
                                    chip._choose()
                                    event.accepted = true
                                }
                            }
                            Keys.onTabPressed:     { event.accepted = true; sidebar._forwardIntoChips(index) }
                            Keys.onRightPressed:   { event.accepted = true; sidebar._forwardIntoChips(index) }
                            Keys.onBacktabPressed: { event.accepted = true; sidebar._backwardOutOfChips(index) }
                            Keys.onLeftPressed:    { event.accepted = true; sidebar._backwardOutOfChips(index) }
                        }
                    }
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
            Keys.onBacktabPressed: { event.accepted = true; sidebar._backwardOutOfChips(sortRepeater.count) }
            Keys.onLeftPressed:    { event.accepted = true; sidebar._backwardOutOfChips(sortRepeater.count) }
        }
    }
}
