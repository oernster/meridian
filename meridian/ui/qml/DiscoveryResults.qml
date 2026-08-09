import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The discovery panel below the search bar: the three placeholder states and
// the results list itself.
//
// Extracted from FeedDiscovery.qml. All four states were siblings in one Item,
// each gated on the same search state, with the list reaching out to the
// enclosing file for the selection, the controller and the toast. The state is
// an input now and every action is a signal.
//
// It owns the second half of the panel's focus ring and hands back through
// focusForwardRequested and focusBackwardRequested, so the search bar and this
// are wired to each other by the caller rather than by name.
Item {
    id: results

    required property var theme
    required property string searchState
    required property string errorMessage
    required property bool hasMore
    required property var candidateModel
    required property var selectedUrls
    required property int selectedCount

    signal toggleRequested(string url)
    signal subscribeRequested(string url, string title)
    signal bulkSubscribeRequested()
    signal focusForwardRequested()
    signal focusBackwardRequested()

    // The bulk button only exists while something is selected, so entering
    // from the search bar has to ask rather than assume.
    function focusFirst() {
        if (bulkBtn.visible) bulkBtn.forceActiveFocus(Qt.TabFocusReason)
        else list.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusListTop() {
        list.currentIndex = 0
        list.forceActiveFocus(Qt.TabFocusReason)
    }

    function _actOnCurrent(subscribe) {
        if (list.currentIndex < 0 || !list.currentItem) return false
        if (list.currentItem.candidateIsSubscribed) return false
        if (subscribe) {
            results.subscribeRequested(
                list.currentItem.candidateUrl,
                list.currentItem.candidateTitle || list.currentItem.candidateUrl
            )
        } else {
            results.toggleRequested(list.currentItem.candidateUrl)
        }
        return true
    }

    // Error state
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 12
        visible: results.searchState === "error"

        Label {
            text: "⚠"
            font.pixelSize: 32
            color: theme.amber
            Layout.alignment: Qt.AlignHCenter
        }
        Label {
            objectName: "errorLabel"
            text: results.errorMessage
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
        objectName: "emptyState"
        anchors.centerIn: parent
        spacing: 12
        visible: results.searchState === "empty"

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
        objectName: "idleState"
        anchors.centerIn: parent
        spacing: 12
        visible: results.searchState === "idle"

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
        objectName: "resultsState"
        anchors.fill: parent
        spacing: 0
        visible: results.searchState === "results"

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
                    id: bulkBtn
                    objectName: "bulkBtn"
                    visible: results.selectedCount > 0
                    height: 26
                    width: bulkLbl.contentWidth + 16
                    radius: 5
                    activeFocusOnTab: true
                    color: bulkMouse.containsMouse ? theme.surface0 : "transparent"
                    border.color: (bulkBtn.activeFocus || bulkMouse.containsMouse) ? theme.amber : theme.green
                    border.width: bulkBtn.activeFocus ? 2 : 1

                    Label {
                        id: bulkLbl
                        objectName: "bulkLabel"
                        anchors.centerIn: parent
                        text: "Subscribe " + results.selectedCount
                        color: theme.green
                        font.pixelSize: 11
                        font.bold: true
                    }
                    MouseArea {
                        id: bulkMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: results.bulkSubscribeRequested()
                    }
                    Keys.onReturnPressed: results.bulkSubscribeRequested()
                    Keys.onPressed: function(event) {
                        if (event.key === Qt.Key_Space) {
                            results.bulkSubscribeRequested()
                            event.accepted = true
                        }
                    }
                    Keys.onTabPressed:     { event.accepted = true; list.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onRightPressed:   { event.accepted = true; list.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onBacktabPressed: { event.accepted = true; results.focusBackwardRequested() }
                    Keys.onLeftPressed:    { event.accepted = true; results.focusBackwardRequested() }
                }
            }
        }

        ListView {
            id: list
            objectName: "resultsList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            activeFocusOnTab: true
            keyNavigationEnabled: true
            model: results.candidateModel
            ScrollBar.vertical: ScrollBar { id: vScroll; policy: ScrollBar.AlwaysOn }

            delegate: CandidateRow {
                width: list.width - vScroll.width
                theme: results.theme
                selected: !!results.selectedUrls[candidateUrl]
                onToggleRequested: results.toggleRequested(candidateUrl)
                onSubscribeRequested: results.subscribeRequested(
                    candidateUrl, candidateTitle || candidateUrl
                )
            }

            Keys.onSpacePressed: function(event) {
                event.accepted = results._actOnCurrent(false)
            }
            Keys.onReturnPressed: function(event) {
                event.accepted = results._actOnCurrent(true)
            }
            Keys.onTabPressed:     { event.accepted = true; results.focusForwardRequested() }
            Keys.onRightPressed:   { event.accepted = true; results.focusForwardRequested() }
            Keys.onBacktabPressed: { event.accepted = true; results._focusBack() }
            Keys.onLeftPressed:    { event.accepted = true; results._focusBack() }

            footer: Rectangle {
                width: list.width
                height: visible ? 48 : 0
                visible: results.hasMore
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

    // Shift+Tab out of the list stops at the bulk button when it is there.
    function _focusBack() {
        if (bulkBtn.visible) bulkBtn.forceActiveFocus(Qt.BacktabFocusReason)
        else results.focusBackwardRequested()
    }
}
