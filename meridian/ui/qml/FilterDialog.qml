import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Set or clear a feed's filter expression.
//
// Extracted from SubscriptionManager.qml. A filter is a single string of terms
// joined by AND, which is unreadable to edit as text, so the dialog splits it
// into a row per term that can be toggled off, with a field for adding one
// more. What comes back out is the join of whatever is still active.
//
// It reports through `filterAccepted` rather than calling the controller. An
// empty result is meaningful: it clears the filter.
FormDialog {
    id: dialog

    property int feedId: 0
    property string feedTitle: ""
    property string currentFilter: ""

    signal filterAccepted(int feedId, string expression)

    readonly property string _separator: " AND "

    title: "Set Filter"
    width: 420

    ListModel { id: terms }

    function _toggle(index) {
        terms.setProperty(index, "active", !terms.get(index).active)
    }

    Label {
        text: "Filter for: " + dialog.feedTitle
        color: dialog.theme.text
        font.bold: true
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    ColumnLayout {
        spacing: 4
        Layout.fillWidth: true
        visible: terms.count > 0

        Label {
            text: "Active filters (Space to toggle):"
            color: dialog.theme.subtext
            font.pixelSize: 11
            font.bold: true
        }

        Repeater {
            id: termRepeater
            model: terms

            delegate: Rectangle {
                id: termRow
                objectName: "termRow" + index
                Layout.fillWidth: true
                height: 30
                radius: 4
                color: termMouse.containsMouse ? dialog.theme.surface0 : "transparent"
                border.color: activeFocus ? dialog.theme.amber : "transparent"
                border.width: 1
                activeFocusOnTab: true

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 6
                    anchors.rightMargin: 6
                    spacing: 8

                    Rectangle {
                        width: 16; height: 16; radius: 3
                        color: model.active ? dialog.theme.blue : "transparent"
                        border.color: dialog.theme.blue
                        border.width: 2
                        Label {
                            anchors.centerIn: parent
                            text: model.active ? "✓" : ""
                            color: dialog.theme.isDark ? "#1e1e2e" : "#ffffff"
                            font.pixelSize: 11; font.bold: true
                        }
                    }

                    Label {
                        text: model.term
                        color: model.active ? dialog.theme.text : dialog.theme.overlay
                        font.pixelSize: 12
                        Layout.fillWidth: true
                        elide: Text.ElideRight
                    }
                }

                MouseArea {
                    id: termMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: dialog._toggle(index)
                }
                Keys.onSpacePressed: { dialog._toggle(index); event.accepted = true }
                Keys.onReturnPressed: { dialog._toggle(index); event.accepted = true }
                Keys.onRightPressed: {
                    var next = termRepeater.itemAt(index + 1)
                    if (next) next.forceActiveFocus()
                    else expressionField.forceActiveFocus()
                    event.accepted = true
                }
                Keys.onLeftPressed: {
                    var previous = termRepeater.itemAt(index - 1)
                    if (previous) previous.forceActiveFocus()
                    event.accepted = true
                }
            }
        }
    }

    Label {
        text: terms.count > 0 ? "Add another filter term:" : "Enter filter expression:"
        color: dialog.theme.subtext
        font.pixelSize: 11
        font.bold: true
    }

    TextField {
        id: expressionField
        objectName: "filterField"
        placeholderText: terms.count > 0
                         ? "e.g. duration:>=300"
                         : "e.g. type:video AND duration:>=300"
        Layout.fillWidth: true
        color: dialog.theme.text
        placeholderTextColor: dialog.theme.overlay
        font.pixelSize: 13
        background: Rectangle {
            color: dialog.theme.surface1
            border.color: expressionField.activeFocus ? dialog.theme.blue : dialog.theme.overlay
            border.width: expressionField.activeFocus ? 2 : 1
            radius: 6
        }
        leftPadding: 10
        rightPadding: 10
        topPadding: 8
        bottomPadding: 8
        Keys.onReturnPressed: { dialog.accept(); event.accepted = true }
    }

    Label {
        text: terms.count > 0
            ? "Deactivate all terms and leave field empty to clear filter"
            : "Leave empty to remove the filter"
        color: dialog.theme.overlay
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }

    onAccepted: {
        var active = []
        for (var i = 0; i < terms.count; i++) {
            var entry = terms.get(i)
            if (entry.active) active.push(entry.term)
        }
        var extra = expressionField.text.trim()
        if (extra) active.push(extra)
        dialog.filterAccepted(dialog.feedId, active.join(dialog._separator))
    }

    onOpened: {
        terms.clear()
        if (dialog.currentFilter) {
            var parts = dialog.currentFilter.split(dialog._separator)
            for (var i = 0; i < parts.length; i++) {
                var term = parts[i].trim()
                if (term) terms.append({ "term": term, "active": true })
            }
        }
        expressionField.text = ""
        if (terms.count > 0) termRepeater.itemAt(0).forceActiveFocus()
        else expressionField.forceActiveFocus()
    }
}
