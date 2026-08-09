import QtQuick
import QtQuick.Controls

// A row of sort chips where the active one is not a tab stop.
//
// Extracted from FeedSidebar.qml and FeedReader.qml, which had written the same
// row out twice, and inside each of them had written the search for "the next
// chip that is not the active one" out six times over. That search is what the
// skip costs: a neighbour cannot simply name the chip beside it.
//
// The two focus functions return whether a chip took focus, because every
// chip being the active one is possible (a single-option row) and the caller
// has somewhere else to go when it happens.
Row {
    id: chips

    required property var theme
    required property var options
    property string current: ""

    signal chosen(string key)

    // Stepping off either end of the row.
    signal forwardOverflow()
    signal backwardOverflow()

    spacing: 4

    function focusFirst() {
        return _focusFrom(-1, 1, Qt.TabFocusReason)
    }

    function focusLast() {
        return _focusFrom(repeater.count, -1, Qt.BacktabFocusReason)
    }

    function _focusFrom(index, step, reason) {
        for (var i = index + step; i >= 0 && i < repeater.count; i += step) {
            var chip = repeater.itemAt(i)
            if (chip && !chip.isActive) {
                chip.forceActiveFocus(reason)
                return true
            }
        }
        return false
    }

    function _forwardFrom(index) {
        if (!chips._focusFrom(index, 1, Qt.TabFocusReason)) chips.forwardOverflow()
    }

    function _backwardFrom(index) {
        if (!chips._focusFrom(index, -1, Qt.BacktabFocusReason)) chips.backwardOverflow()
    }

    Repeater {
        id: repeater
        model: chips.options

        delegate: Rectangle {
            id: chip
            objectName: "sortChip_" + modelData.key
            property bool isActive: chips.current === modelData.key
            property bool hovered: false
            height: 26; radius: 4
            implicitWidth: chipLabel.implicitWidth + 12
            activeFocusOnTab: !isActive
            color: isActive ? theme.surface0 : "transparent"
            border.color: isActive ? theme.blue
                        : (hovered || activeFocus) ? theme.amber : "transparent"
            border.width: activeFocus ? 2 : 1

            function _choose() {
                if (chip.isActive) return
                chips.chosen(modelData.key)
            }

            Label {
                id: chipLabel
                anchors.centerIn: parent
                text: modelData.label
                color: chip.isActive ? theme.blue
                     : (chip.hovered || chip.activeFocus) ? theme.text : theme.overlay
                font.pixelSize: 10
                font.bold: chip.isActive
            }

            HoverHandler { onHoveredChanged: chip.hovered = hovered }

            MouseArea {
                anchors.fill: parent
                enabled: !chip.isActive
                cursorShape: chip.isActive ? Qt.ArrowCursor : Qt.PointingHandCursor
                onClicked: chip._choose()
            }

            Keys.onReturnPressed: chip._choose()
            Keys.onPressed: function(event) {
                if (event.key === Qt.Key_Space) {
                    chip._choose()
                    event.accepted = true
                }
            }
            Keys.onTabPressed:     { event.accepted = true; chips._forwardFrom(index) }
            Keys.onRightPressed:   { event.accepted = true; chips._forwardFrom(index) }
            Keys.onBacktabPressed: { event.accepted = true; chips._backwardFrom(index) }
            Keys.onLeftPressed:    { event.accepted = true; chips._backwardFrom(index) }
        }
    }
}
