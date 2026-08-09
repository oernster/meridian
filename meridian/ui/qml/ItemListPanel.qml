import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The reader's left-hand panel: the sort chips, mark-all-read, and the list of
// items in the selected feed.
//
// Extracted from FeedReader.qml. Selecting a row, whether by click or by
// walking the list with the keyboard, reports the item outwards rather than
// loading the detail pane itself.
//
// The role offsets are gathered in one place because the panel reads the model
// directly: a delegate for a row that has not been realised does not exist, so
// `currentItem` cannot be relied on to answer what the current row holds.
Rectangle {
    id: panel

    required property var theme
    required property var itemModel
    property string sort: "newest"

    signal sortChosen(string key)
    signal markAllReadRequested()
    signal itemSelected(int itemId, var item)
    signal focusForwardRequested()
    signal focusBackwardRequested()

    readonly property var _sortOptions: [
        { key: "newest", label: "Newest" },
        { key: "oldest", label: "Oldest" },
        { key: "alpha",  label: "A→Z"    }
    ]

    readonly property var _roles: ({
        "id": Qt.UserRole,
        "title": Qt.UserRole + 1,
        "type": Qt.UserRole + 2,
        "url": Qt.UserRole + 3,
        "published": Qt.UserRole + 4,
        "thumbnail": Qt.UserRole + 5,
        "description": Qt.UserRole + 8,
        "mediaUrl": Qt.UserRole + 10
    })

    color: theme.mantle

    function focusList() {
        itemList.forceActiveFocus(Qt.TabFocusReason)
    }

    function _selectRow(row) {
        if (row < 0) return
        var index = panel.itemModel.index(row, 0)
        function value(role) { return panel.itemModel.data(index, panel._roles[role]) }
        panel.itemSelected(value("id"), {
            itemTitle:       value("title"),
            itemPublished:   value("published"),
            itemType:        value("type"),
            itemDescription: value("description"),
            itemUrl:         value("url"),
            itemMediaUrl:    value("mediaUrl"),
            itemThumbnail:   value("thumbnail")
        })
    }

    // Shared by the item rows and by the detail pane's duration caption.
    function formatDuration(seconds) {
        const s = Math.floor(seconds)
        const h = Math.floor(s / 3600)
        const m = Math.floor((s % 3600) / 60)
        const sec = s % 60
        if (h > 0)
            return h + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
        return String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Panel header
        Rectangle {
            Layout.fillWidth: true
            height: 48
            color: theme.mantle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 8

                Label {
                    text: "Items"
                    font.pixelSize: 14
                    font.bold: true
                    color: theme.text
                    Layout.fillWidth: true
                }

                SortChipRow {
                    id: sortChips
                    theme: panel.theme
                    options: panel._sortOptions
                    current: panel.sort
                    onChosen: function(key) { panel.sortChosen(key) }
                    onForwardOverflow: markAllReadBtn.forceActiveFocus(Qt.TabFocusReason)
                    onBackwardOverflow: panel.focusBackwardRequested()
                }

                Button {
                    id: markAllReadBtn
                    objectName: "markAllReadBtn"
                    flat: true
                    font.pixelSize: 11
                    implicitHeight: 30
                    activeFocusOnTab: true
                    onClicked: panel.markAllReadRequested()
                    contentItem: Label {
                        text: "Mark all read"
                        color: theme.subtext
                        font.pixelSize: 11
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: markAllReadBtn.pressed ? theme.surface1
                             : markAllReadBtn.hovered ? theme.surface0
                             : "transparent"
                        border.color: (markAllReadBtn.hovered || markAllReadBtn.activeFocus)
                                      ? theme.amber : "transparent"
                        border.width: 1
                        radius: 5
                    }
                    Keys.onTabPressed:     { event.accepted = true; itemList.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onRightPressed:   { event.accepted = true; itemList.forceActiveFocus(Qt.TabFocusReason) }
                    Keys.onBacktabPressed: { event.accepted = true; panel._backFromMarkAll() }
                    Keys.onLeftPressed:    { event.accepted = true; panel._backFromMarkAll() }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.surface0
            }
        }

        ListView {
            id: itemList
            objectName: "itemList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: panel.itemModel
            currentIndex: -1
            activeFocusOnTab: true
            keyNavigationEnabled: true
            ScrollBar.vertical: ScrollBar { id: vScroll; policy: ScrollBar.AlwaysOn }

            delegate: ItemRow {
                width: itemList.width - vScroll.width
                theme: panel.theme
                durationText: itemDuration > 0 ? panel.formatDuration(itemDuration) : ""
                onActivated: {
                    itemList.currentIndex = index
                    panel._selectRow(index)
                }
            }

            onActiveFocusChanged: {
                if (activeFocus && currentIndex < 0 && count > 0) currentIndex = 0
            }
            onCurrentIndexChanged: {
                if (activeFocus && currentIndex >= 0) panel._selectRow(currentIndex)
            }

            Keys.onTabPressed:     { event.accepted = true; panel.focusForwardRequested() }
            Keys.onRightPressed:   { event.accepted = true; panel.focusForwardRequested() }
            Keys.onBacktabPressed: { event.accepted = true; markAllReadBtn.forceActiveFocus(Qt.BacktabFocusReason) }
            Keys.onLeftPressed:    { event.accepted = true; markAllReadBtn.forceActiveFocus(Qt.BacktabFocusReason) }
        }
    }

    function _backFromMarkAll() {
        if (!sortChips.focusLast()) panel.focusBackwardRequested()
    }
}
