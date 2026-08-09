import QtQuick
import QtQuick.Controls

// The discovery search field with its topic autocomplete.
//
// Extracted from FeedDiscovery.qml together with the debounce timer and the
// suggestion fetch that drive it. Those three were separate top-level pieces
// of that file with the popup wired between them by id, so the ordering rules
// (a keystroke restarts the debounce, the debounce aborts the in-flight
// request, a reply opens the popup only while the field still has focus) were
// spread across the whole file. They are all here now.
//
// The field owns its popup completely: it dismisses it before emitting
// searchRequested, so no caller has to know the popup exists.
Item {
    id: queryRoot

    required property var theme

    // Escape means different things while a search is running.
    required property string searchState

    readonly property alias text: field.text

    signal searchRequested()
    signal cancelRequested()
    signal closeRequested()
    signal focusForwardRequested()

    // Below this the field is treated as too short to suggest against, so no
    // request is made and any open popup is dismissed.
    readonly property int _minimumQueryLength: 2

    // Long enough that typing a word does not fire a request per keystroke,
    // short enough that the list arrives while the user is still looking.
    readonly property int _debounceMs: 250

    readonly property int _suggestionLimit: 10

    readonly property string _suggestionEndpoint:
        "https://en.wikipedia.org/w/api.php?action=opensearch&format=json&namespace=0"

    property var _suggestions: []
    property var _currentXhr: null

    implicitHeight: field.implicitHeight

    function focusField() {
        field.forceActiveFocus(Qt.TabFocusReason)
    }

    function dismissAutocomplete() {
        suggestionList.currentIndex = -1
        suggestionPopup.close()
    }

    function _acceptSuggestion(suggestion) {
        field.text = suggestion
        queryRoot.dismissAutocomplete()
    }

    function _fetchSuggestions(query) {
        if (queryRoot._currentXhr) {
            queryRoot._currentXhr.abort()
            queryRoot._currentXhr = null
        }
        if (query.length < queryRoot._minimumQueryLength) {
            queryRoot._suggestions = []
            suggestionPopup.close()
            return
        }
        var xhr = new XMLHttpRequest()
        queryRoot._currentXhr = xhr
        xhr.onreadystatechange = function() {
            if (xhr.readyState !== XMLHttpRequest.DONE) return
            queryRoot._currentXhr = null
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText)
                    queryRoot._suggestions = data[1] || []
                } catch(e) {
                    queryRoot._suggestions = []
                }
            } else {
                queryRoot._suggestions = []
            }
            if (queryRoot._suggestions.length > 0 && field.activeFocus) {
                suggestionPopup.open()
            } else {
                suggestionPopup.close()
            }
        }
        xhr.open("GET", queryRoot._suggestionEndpoint
                        + "&limit=" + queryRoot._suggestionLimit
                        + "&search=" + encodeURIComponent(query))
        xhr.send()
    }

    Timer {
        id: debounce
        objectName: "suggestionDebounce"
        interval: queryRoot._debounceMs
        repeat: false
        onTriggered: queryRoot._fetchSuggestions(field.text.trim())
    }

    TextField {
        id: field
        // Named because focus lands here rather than on the component root,
        // which is what tests/ui/test_discovery_focus_ring.py reads.
        objectName: "queryInput"
        width: parent.width
        placeholderText: "e.g. Python, Technology, Science..."
        color: theme.text
        placeholderTextColor: theme.overlay
        font.pixelSize: 13
        background: Rectangle {
            color: theme.base
            border.color: field.activeFocus ? theme.blue : theme.surface1
            border.width: field.activeFocus ? 2 : 1
            radius: 6
        }
        leftPadding: 10
        rightPadding: 10
        topPadding: 8
        bottomPadding: 8

        Keys.onReturnPressed: function(event) {
            if (suggestionPopup.visible && suggestionList.currentIndex >= 0) {
                queryRoot._acceptSuggestion(suggestionList.model[suggestionList.currentIndex])
            } else {
                queryRoot.dismissAutocomplete()
                queryRoot.searchRequested()
            }
            event.accepted = true
        }
        Keys.onDownPressed: function(event) {
            if (suggestionPopup.visible) {
                suggestionList.currentIndex = Math.min(
                    suggestionList.currentIndex + 1,
                    suggestionList.count - 1
                )
                suggestionList.positionViewAtIndex(
                    suggestionList.currentIndex, ListView.Contain
                )
                event.accepted = true
            }
        }
        Keys.onUpPressed: function(event) {
            if (suggestionPopup.visible) {
                suggestionList.currentIndex = Math.max(
                    suggestionList.currentIndex - 1, -1
                )
                if (suggestionList.currentIndex >= 0) {
                    suggestionList.positionViewAtIndex(
                        suggestionList.currentIndex, ListView.Contain
                    )
                }
                event.accepted = true
            }
        }
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space
                    && suggestionPopup.visible
                    && suggestionList.currentIndex >= 0) {
                queryRoot._acceptSuggestion(suggestionList.model[suggestionList.currentIndex])
                event.accepted = true
            }
        }
        Keys.onTabPressed: function(event) {
            event.accepted = true
            queryRoot.dismissAutocomplete()
            queryRoot.focusForwardRequested()
        }
        Keys.onEscapePressed: {
            if (suggestionPopup.visible) {
                queryRoot.dismissAutocomplete()
            } else if (queryRoot.searchState === "searching") {
                queryRoot.cancelRequested()
            } else {
                queryRoot.closeRequested()
            }
        }
        onTextChanged: {
            suggestionList.currentIndex = -1
            if (text.trim().length >= queryRoot._minimumQueryLength) {
                debounce.restart()
            } else {
                debounce.stop()
                queryRoot._suggestions = []
                suggestionPopup.close()
            }
        }
    }

    Popup {
        id: suggestionPopup
        objectName: "suggestionPopup"
        y: field.height + 2
        width: field.width
        padding: 4
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle {
            color: theme.mantle
            border.color: theme.surface0
            border.width: 1
            radius: 6
        }

        contentItem: ListView {
            id: suggestionList
            objectName: "suggestionList"
            currentIndex: -1
            implicitHeight: Math.min(contentHeight, 180)
            clip: true
            model: queryRoot._suggestions
            delegate: Rectangle {
                width: suggestionList.width
                height: 32
                color: (index === suggestionList.currentIndex || acHover.containsMouse)
                       ? theme.surface0 : "transparent"
                radius: 4
                Label {
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 8
                    text: modelData
                    color: index === suggestionList.currentIndex ? theme.blue : theme.text
                    font.pixelSize: 13
                    font.bold: index === suggestionList.currentIndex
                }
                MouseArea {
                    id: acHover
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        queryRoot._acceptSuggestion(modelData)
                        queryRoot.focusField()
                    }
                }
            }
        }
    }
}
