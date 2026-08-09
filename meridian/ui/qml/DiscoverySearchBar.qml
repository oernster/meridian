import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The discovery panel's search section: heading, query field, result cap and
// the Search/Cancel button, with the busy row underneath.
//
// Extracted from FeedDiscovery.qml. It owns the first half of the panel's
// focus ring (field, cap, button) and hands over at each end through
// focusForwardRequested and the two focus functions, so it names nothing
// outside itself. The caller decides what lies on either side.
Rectangle {
    id: bar

    required property var theme
    required property string searchState
    required property var capOptions
    property int capIndex: 0

    readonly property alias queryText: queryField.text

    signal searchRequested()
    signal cancelRequested()
    signal closeRequested()
    signal capChosen(int cap)
    signal focusForwardRequested()

    // The button is only a tab stop when there is something to search for, so
    // both ends of the ring have to ask rather than assume.
    function focusFirst() {
        queryField.focusField()
    }

    function focusLast() {
        if (searchBtn.activeFocusOnTab) searchBtn.forceActiveFocus(Qt.BacktabFocusReason)
        else capCombo.forceActiveFocus(Qt.BacktabFocusReason)
    }

    function dismissAutocomplete() {
        queryField.dismissAutocomplete()
    }

    function _submit() {
        if (bar.searchState === "searching") bar.cancelRequested()
        else { queryField.dismissAutocomplete(); bar.searchRequested() }
    }

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

        DiscoveryQueryField {
            id: queryField
            objectName: "queryField"
            Layout.fillWidth: true
            theme: bar.theme
            searchState: bar.searchState
            onSearchRequested: bar.searchRequested()
            onCancelRequested: bar.cancelRequested()
            onCloseRequested: bar.closeRequested()
            onFocusForwardRequested: capCombo.forceActiveFocus(Qt.TabFocusReason)
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
                objectName: "capCombo"
                model: bar.capOptions
                currentIndex: bar.capIndex
                implicitWidth: 72
                implicitHeight: 34
                font.pixelSize: 12
                onCurrentIndexChanged: bar.capChosen(bar.capOptions[currentIndex])
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
                    else bar.focusForwardRequested()
                }
                Keys.onRightPressed: {
                    event.accepted = true
                    if (searchBtn.activeFocusOnTab) searchBtn.forceActiveFocus(Qt.TabFocusReason)
                    else bar.focusForwardRequested()
                }
            }

            Item { Layout.fillWidth: true }

            Rectangle {
                id: searchBtn
                objectName: "searchBtn"
                height: 34
                width: searchBtnLbl.contentWidth + 28
                radius: 8
                activeFocusOnTab: bar.queryText.trim().length > 0
                color: {
                    if (bar.searchState === "searching") return theme.surface1
                    return searchBtnMouse.containsMouse ? theme.blue + "dd" : theme.blue
                }
                border.color: (searchBtnMouse.containsMouse || activeFocus) ? theme.amber : "transparent"
                border.width: activeFocus ? 2 : 1

                Label {
                    id: searchBtnLbl
                    objectName: "searchBtnLabel"
                    anchors.centerIn: parent
                    text: bar.searchState === "searching" ? "✕  Cancel" : "🔍  Search"
                    color: theme.isDark ? "#1e1e2e" : "#ffffff"
                    font.pixelSize: 13
                    font.bold: true
                }

                MouseArea {
                    id: searchBtnMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: bar._submit()
                }
                Keys.onReturnPressed: bar._submit()
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space) {
                        bar._submit()
                        event.accepted = true
                    }
                }
                Keys.onTabPressed:     { event.accepted = true; bar.focusForwardRequested() }
                Keys.onRightPressed:   { event.accepted = true; bar.focusForwardRequested() }
                Keys.onBacktabPressed: { event.accepted = true; capCombo.forceActiveFocus(Qt.BacktabFocusReason) }
                Keys.onLeftPressed:    { event.accepted = true; capCombo.forceActiveFocus(Qt.BacktabFocusReason) }
            }
        }

        // Loading indicator
        RowLayout {
            visible: bar.searchState === "searching"
            Layout.fillWidth: true
            spacing: 10

            BusyIndicator {
                running: bar.searchState === "searching"
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
