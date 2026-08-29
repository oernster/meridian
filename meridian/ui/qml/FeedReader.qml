import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Qt.labs.settings

// The two-panel reader: the item list on the left, the item itself on the
// right.
//
// What is left here after the split is the join between the two halves, the
// stored playback volume, the wiring to the controller. Selecting a row
// reports outwards from the list; loading the detail pane and marking the item
// read both happen here, because neither panel should know the other exists.
Item {
    id: root

    required property var theme
    // The stop the ring continues to when Tab leaves the reader. It was the
    // header's first button until the window grew a foot; the reader does not
    // know or care which band it lands in, so it is named for what it is.
    property var wrapForwardItem: null

    // The window wraps its own Tab chain back through this.
    readonly property alias lastFocusItem: detailPane.lastFocusItem

    Settings {
        id: appSettings
        category: "Player"
        property real volume: 0.2
    }

    Connections {
        target: controller
        function onItemsChanged() {
            if (controller.itemModel.rowCount() === 0) detailPane.clear()
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        ItemListPanel {
            id: listPanel
            objectName: "listPanel"
            Layout.preferredWidth: 360
            Layout.fillHeight: true
            theme: root.theme
            itemModel: controller ? controller.itemModel : null

            onSortChosen: function(key) {
                listPanel.sort = key
                controller.setItemSort(key)
            }
            onMarkAllReadRequested: {
                if (controller.selectedFeedId > 0)
                    controller.markAllRead(controller.selectedFeedId)
            }
            onItemSelected: function(itemId, item) {
                detailPane.load(item)
                controller.markRead(itemId)
            }
            onFocusForwardRequested: detailPane.focusFirst()
            onFocusBackwardRequested: {
                var previous = listPanel.nextItemInFocusChain(false)
                if (previous && previous !== listPanel)
                    previous.forceActiveFocus(Qt.BacktabFocusReason)
            }
        }

        // Divider
        Rectangle {
            width: 1
            Layout.fillHeight: true
            color: theme.surface0
        }

        ItemDetailPane {
            id: detailPane
            objectName: "detailPane"
            Layout.fillWidth: true
            Layout.fillHeight: true
            theme: root.theme
            initialVolume: appSettings.volume

            onVolumeChosen: function(value) { appSettings.volume = value }
            onFocusForwardRequested: {
                if (root.wrapForwardItem)
                    root.wrapForwardItem.forceActiveFocus(Qt.TabFocusReason)
            }
            onFocusBackwardRequested: listPanel.focusList()
        }
    }
}
