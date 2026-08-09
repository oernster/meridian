import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The subscription manager drawer: composition, the selection, plus the dialogs
// the list rows ask for.
//
// What is left here after the split is the selection (which the list header
// shows, the rows toggle and the removal confirmation consumes), the list
// itself, plus the wiring from each panel's signals to the controller. The add
// bar and the rows name nothing outside themselves.
Rectangle {
    id: root
    required property var theme
    signal close()

    color: theme.base

    property var selectedIds: ({})
    property int selectedCount: 0
    property var _allIds: []

    function _registerId(feedId) {
        var a = _allIds.slice(); a.push(feedId); _allIds = a
    }
    function _unregisterId(feedId) {
        _allIds = _allIds.filter(function(x) { return x !== feedId })
        toggleSelected(feedId, false)
    }
    function toggleSelected(feedId, forceState) {
        var s = Object.assign({}, selectedIds)
        var on = (forceState !== undefined) ? forceState : !s[feedId]
        if (on) { s[feedId] = true } else { delete s[feedId] }
        selectedIds = s
        selectedCount = Object.keys(selectedIds).length
    }
    function selectAll() {
        var s = {}
        var model = controller.feedModel
        for (var i = 0; i < model.rowCount(); i++) {
            var id = model.data(model.index(i, 0), Qt.UserRole)
            s[id] = true
        }
        selectedIds = s
        selectedCount = Object.keys(s).length
    }
    function clearSelection() { selectedIds = {}; selectedCount = 0 }
    function focusUrlField() { addBar.focusFirst() }

    function _toggleAll() {
        if (root.selectedCount === controller.feedModel.rowCount()) root.clearSelection()
        else root.selectAll()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 56
            color: theme.mantle

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 16
                anchors.rightMargin: 12

                Label {
                    text: "Subscriptions"
                    font.pixelSize: 17
                    font.bold: true
                    color: theme.text
                    Layout.fillWidth: true
                }

                Button {
                    flat: true
                    implicitWidth: 36
                    implicitHeight: 36
                    onClicked: root.close()
                    contentItem: Label {
                        text: "✕"
                        color: theme.subtext
                        font.pixelSize: 15
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    background: Rectangle {
                        color: parent.pressed ? theme.surface1
                             : parent.hovered ? theme.surface0
                             : "transparent"
                        border.color: parent.hovered ? theme.amber : "transparent"
                        border.width: 1
                        radius: 6
                    }
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.surface0
            }
        }

        AddSubscriptionBar {
            id: addBar
            objectName: "addBar"
            Layout.fillWidth: true
            theme: root.theme
            onSubscribeRequested: function(url) { controller.subscribe(url) }
            onFocusForwardRequested: selectAllCheckbox.forceActiveFocus()
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme.surface0
        }

        // Subscription list header
        Rectangle {
            Layout.fillWidth: true
            height: 36
            color: theme.base

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 8

                Rectangle {
                    id: selectAllCheckbox
                    objectName: "selectAllCheckbox"
                    width: 18; height: 18; radius: 3
                    activeFocusOnTab: true
                    color: (root.selectedCount > 0) ? theme.blue : "transparent"
                    border.color: activeFocus ? theme.amber : theme.blue
                    border.width: 2
                    Label {
                        anchors.centerIn: parent
                        text: root.selectedCount === 0 ? ""
                            : root.selectedCount === controller.feedModel.rowCount() ? "✓" : "–"
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 12; font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root._toggleAll()
                    }
                    Keys.onSpacePressed: root._toggleAll()
                    Keys.onReturnPressed: root._toggleAll()
                    Keys.onTabPressed: { (removeSelBtn.visible ? removeSelBtn : subList).forceActiveFocus(); event.accepted = true }
                    Keys.onRightPressed: { (removeSelBtn.visible ? removeSelBtn : subList).forceActiveFocus(); event.accepted = true }
                    Keys.onBacktabPressed: { addBar.focusLast(); event.accepted = true }
                    Keys.onLeftPressed: { addBar.focusLast(); event.accepted = true }
                }

                Label {
                    text: "SUBSCRIBED FEEDS"
                    font.pixelSize: 11
                    font.bold: true
                    font.letterSpacing: 1.2
                    color: theme.overlay
                    Layout.fillWidth: true
                }

                Rectangle {
                    id: removeSelBtn
                    objectName: "removeSelBtn"
                    visible: root.selectedCount > 0
                    activeFocusOnTab: visible
                    height: 26
                    width: removeSelLbl.contentWidth + 16
                    radius: 5
                    color: removeSelMouse.containsMouse ? theme.surface0 : "transparent"
                    border.color: activeFocus ? theme.amber : theme.red
                    border.width: 1

                    Label {
                        id: removeSelLbl
                        anchors.centerIn: parent
                        text: "Remove " + root.selectedCount
                        color: theme.red
                        font.pixelSize: 11
                        font.bold: true
                    }

                    MouseArea {
                        id: removeSelMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bulkRemoveDialog.open()
                    }
                    Keys.onSpacePressed: { bulkRemoveDialog.open(); event.accepted = true }
                    Keys.onReturnPressed: { bulkRemoveDialog.open(); event.accepted = true }
                    Keys.onTabPressed: { subList.forceActiveFocus(); event.accepted = true }
                    Keys.onRightPressed: { subList.forceActiveFocus(); event.accepted = true }
                    Keys.onBacktabPressed: { selectAllCheckbox.forceActiveFocus(); event.accepted = true }
                    Keys.onLeftPressed: { selectAllCheckbox.forceActiveFocus(); event.accepted = true }
                }
            }
        }

        ListView {
            id: subList
            objectName: "subList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: controller ? controller.feedModel : null
            ScrollBar.vertical: ScrollBar { id: subVScroll; policy: ScrollBar.AlwaysOn }
            activeFocusOnTab: true
            keyNavigationEnabled: true

            delegate: SubscriptionRow {
                width: subList.width - subVScroll.width
                theme: root.theme
                selected: !!root.selectedIds[feedId]

                Component.onCompleted: root._registerId(feedId)
                Component.onDestruction: root._unregisterId(feedId)

                onToggleRequested: root.toggleSelected(feedId)
                onFilterRequested: {
                    filterDialog.feedId = feedId
                    filterDialog.feedTitle = feedTitle || feedUrl
                    filterDialog.currentFilter = feedFilter
                    filterDialog.open()
                }
                onEditRequested: {
                    editUrlDialog.feedId = feedId
                    editUrlDialog.currentUrl = feedUrl
                    editUrlDialog.open()
                }
                onRemoveRequested: {
                    root.toggleSelected(feedId, true)
                    bulkRemoveDialog.open()
                }
            }

            Keys.onBacktabPressed: { (removeSelBtn.visible ? removeSelBtn : selectAllCheckbox).forceActiveFocus(); event.accepted = true }
            Keys.onLeftPressed: { (removeSelBtn.visible ? removeSelBtn : selectAllCheckbox).forceActiveFocus(); event.accepted = true }
            Keys.onSpacePressed: {
                if (currentIndex >= 0) {
                    var feedId = model.data(model.index(currentIndex, 0), Qt.UserRole)
                    root.toggleSelected(feedId)
                }
            }
            onActiveFocusChanged: {
                if (activeFocus && currentIndex < 0 && count > 0)
                    currentIndex = 0
            }
        }
    }

    ConfirmDialog {
        id: bulkRemoveDialog
        objectName: "bulkRemoveDialog"
        theme: root.theme
        title: "Remove Subscriptions"
        bodyWidth: 300
        message: "Remove " + root.selectedCount
               + " feed(s)?\nAll downloaded items will be deleted."
        onAccepted: {
            var ids = Object.keys(root.selectedIds).map(function(k) { return parseInt(k) })
            root.clearSelection()
            controller.bulkUnsubscribe(ids)
        }
    }

    EditUrlDialog {
        id: editUrlDialog
        objectName: "editUrlDialog"
        theme: root.theme
        onUrlAccepted: function(feedId, url) { controller.updateFeedUrl(feedId, url) }
    }

    FilterDialog {
        id: filterDialog
        objectName: "filterDialog"
        theme: root.theme
        onFilterAccepted: function(feedId, expression) {
            controller.setFilter(feedId, expression)
        }
    }
}
