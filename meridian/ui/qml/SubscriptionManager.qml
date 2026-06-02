import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

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
    function focusUrlField() { urlField.forceActiveFocus() }

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

        // Add subscription section
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: addCol.implicitHeight + 32
            color: theme.mantle

            ColumnLayout {
                id: addCol
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 16
                spacing: 10

                Label {
                    text: "Add Subscription"
                    font.pixelSize: 13
                    font.bold: true
                    color: theme.subtext
                    font.letterSpacing: 0.6
                }

                TextField {
                    id: urlField
                    placeholderText: "https://example.com/.well-known/mmsp.json"
                    Layout.fillWidth: true
                    color: theme.text
                    placeholderTextColor: theme.overlay
                    font.pixelSize: 13
                    background: Rectangle {
                        color: theme.base
                        border.color: parent.activeFocus ? theme.blue : theme.surface1
                        border.width: parent.activeFocus ? 2 : 1
                        radius: 6
                    }
                    leftPadding: 10
                    rightPadding: 10
                    topPadding: 8
                    bottomPadding: 8
                    Keys.onRightPressed: { selectAllCheckbox.forceActiveFocus(); event.accepted = true }
                }


                Rectangle {
                    id: subscribeRect
                    Layout.fillWidth: true
                    height: 38
                    radius: 8
                    activeFocusOnTab: urlField.text.trim().startsWith("https://")
                    color: subscribeBtn.pressed ? theme.blue + "cc"
                         : urlField.text.trim().startsWith("https://") ? (subscribeBtn.containsMouse ? theme.blue + "dd" : theme.blue)
                         : theme.surface1
                    opacity: urlField.text.trim().startsWith("https://") ? 1.0 : 0.5
                    border.color: (activeFocus || (subscribeBtn.containsMouse && urlField.text.trim().startsWith("https://"))) ? theme.amber : "transparent"
                    border.width: 1
                    Keys.onReturnPressed: {
                        if (urlField.text.trim().startsWith("https://")) {
                            controller.subscribe(urlField.text.trim())
                            urlField.text = ""
                            event.accepted = true
                        }
                    }
                    Keys.onSpacePressed: {
                        if (urlField.text.trim().startsWith("https://")) {
                            controller.subscribe(urlField.text.trim())
                            urlField.text = ""
                            event.accepted = true
                        }
                    }

                    Label {
                        anchors.centerIn: parent
                        text: "Subscribe"
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 13
                        font.bold: true
                    }

                    MouseArea {
                        id: subscribeBtn
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: urlField.text.trim().startsWith("https://") ? Qt.PointingHandCursor : Qt.ArrowCursor
                        property bool pressed: false
                        property bool containsMouse: false
                        enabled: urlField.text.trim().startsWith("https://")
                        onEntered: containsMouse = true
                        onExited: containsMouse = false
                        onPressed: pressed = true
                        onReleased: pressed = false
                        onClicked: {
                            controller.subscribe(urlField.text.trim())
                            urlField.text = ""
                        }
                    }
                }

                Item { height: 4 }
            }
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
                    width: 18; height: 18; radius: 3
                    activeFocusOnTab: true
                    color: (root.selectedCount > 0) ? theme.blue : "transparent"
                    border.color: activeFocus ? theme.amber : theme.blue
                    border.width: activeFocus ? 2 : 2
                    Label {
                        anchors.centerIn: parent
                        text: root.selectedCount > 0 && root.selectedCount === controller.feedModel.rowCount() ? "✓" : (root.selectedCount > 0 ? "–" : "")
                        color: theme.isDark ? "#1e1e2e" : "#ffffff"
                        font.pixelSize: 12; font.bold: true
                    }
                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.selectedCount === controller.feedModel.rowCount() ? root.clearSelection() : root.selectAll()
                    }
                    Keys.onSpacePressed: root.selectedCount === controller.feedModel.rowCount() ? root.clearSelection() : root.selectAll()
                    Keys.onReturnPressed: root.selectedCount === controller.feedModel.rowCount() ? root.clearSelection() : root.selectAll()
                    Keys.onTabPressed: { (removeSelBtn.visible ? removeSelBtn : subList).forceActiveFocus(); event.accepted = true }
                    Keys.onRightPressed: { (removeSelBtn.visible ? removeSelBtn : subList).forceActiveFocus(); event.accepted = true }
                    Keys.onBacktabPressed: { (subscribeRect.activeFocusOnTab ? subscribeRect : urlField).forceActiveFocus(); event.accepted = true }
                    Keys.onLeftPressed: { (subscribeRect.activeFocusOnTab ? subscribeRect : urlField).forceActiveFocus(); event.accepted = true }
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
                        onClicked: bulkConfirmDialog.open()
                    }
                    Keys.onSpacePressed: { bulkConfirmDialog.open(); event.accepted = true }
                    Keys.onReturnPressed: { bulkConfirmDialog.open(); event.accepted = true }
                    Keys.onTabPressed: { subList.forceActiveFocus(); event.accepted = true }
                    Keys.onRightPressed: { subList.forceActiveFocus(); event.accepted = true }
                    Keys.onBacktabPressed: { selectAllCheckbox.forceActiveFocus(); event.accepted = true }
                    Keys.onLeftPressed: { selectAllCheckbox.forceActiveFocus(); event.accepted = true }
                }
            }
        }

        ListView {
            id: subList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: controller ? controller.feedModel : null
            delegate: subDelegate
            ScrollBar.vertical: ScrollBar { id: subVScroll; policy: ScrollBar.AlwaysOn }
            activeFocusOnTab: true
            keyNavigationEnabled: true
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

    Dialog {
        id: bulkConfirmDialog
        title: "Remove Subscriptions"
        modal: true
        anchors.centerIn: Overlay.overlay
        background: Rectangle { color: theme.base; border.color: theme.surface0; radius: 8 }
        footer: Rectangle {
            color: theme.mantle
            implicitHeight: 52
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                StyledButton {
                    id: bulkCancelBtn
                    text: "Cancel"; theme: root.theme; onClicked: bulkConfirmDialog.reject()
                    Keys.onReturnPressed: { bulkConfirmDialog.reject(); event.accepted = true }
                    Keys.onRightPressed: { bulkOkBtn.forceActiveFocus(); event.accepted = true }
                }
                StyledButton {
                    id: bulkOkBtn
                    text: "OK"; theme: root.theme; onClicked: bulkConfirmDialog.accept()
                    Keys.onReturnPressed: { bulkConfirmDialog.accept(); event.accepted = true }
                    Keys.onLeftPressed: { bulkCancelBtn.forceActiveFocus(); event.accepted = true }
                }
            }
        }
        Label {
            text: "Remove " + root.selectedCount + " feed(s)?\nAll downloaded items will be deleted."
            wrapMode: Text.WordWrap
            width: 300
            color: theme.text
            lineHeight: 1.4
        }
        onAccepted: {
            var ids = Object.keys(root.selectedIds).map(function(k) { return parseInt(k) })
            root.clearSelection()
            controller.bulkUnsubscribe(ids)
        }
    }

    // Subscription list delegate
    Component {
        id: subDelegate

        Rectangle {
            id: delegateRoot
            width: subList.width - subVScroll.width
            height: 80 + (model.feedFilter !== "" ? 18 : 0) + (model.feedDescription !== "" ? 18 : 0)
            color: (!!root.selectedIds[model.feedId] || subItemMouse.hovered || ListView.isCurrentItem) ? theme.mantle : theme.base
            border.color: (subItemMouse.hovered || ListView.isCurrentItem) ? theme.amber : "transparent"
            border.width: 2

            Component.onCompleted: root._registerId(model.feedId)
            Component.onDestruction: root._unregisterId(model.feedId)

            ColumnLayout {
                anchors.fill: parent
                anchors.leftMargin: 8
                anchors.rightMargin: 12
                anchors.topMargin: 10
                anchors.bottomMargin: 10
                spacing: 4

                // Normal row
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 6
                    visible: true

                    Rectangle {
                        id: rowCb
                        width: 18; height: 18; radius: 3
                        activeFocusOnTab: true
                        color: !!root.selectedIds[model.feedId] ? theme.blue : "transparent"
                        border.color: activeFocus ? theme.amber : theme.blue
                        border.width: 2
                        Label {
                            anchors.centerIn: parent
                            text: !!root.selectedIds[model.feedId] ? "✓" : ""
                            color: theme.isDark ? "#1e1e2e" : "#ffffff"
                            font.pixelSize: 12; font.bold: true
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.toggleSelected(model.feedId)
                        }
                        Keys.onSpacePressed: { root.toggleSelected(model.feedId); event.accepted = true }
                        Keys.onReturnPressed: { root.toggleSelected(model.feedId); event.accepted = true }
                        Keys.onRightPressed: { filterBtn.forceActiveFocus(); event.accepted = true }
                    }

                    Label {
                        text: model.feedTitle || model.feedUrl
                        color: theme.text
                        font.pixelSize: 13
                        font.bold: true
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Button {
                        id: filterBtn
                        flat: true
                        font.pixelSize: 11
                        implicitHeight: 26
                        implicitWidth: 52
                        onClicked: {
                            filterDialog.feedId = model.feedId
                            filterDialog.feedTitle = model.feedTitle || model.feedUrl
                            filterDialog.currentFilter = model.feedFilter
                            filterDialog.open()
                        }
                        contentItem: Label {
                            text: "Filter"
                            color: theme.blue
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            color: parent.pressed ? theme.surface1
                                 : parent.hovered ? theme.surface0
                                 : "transparent"
                            border.color: (parent.activeFocus || parent.hovered) ? theme.amber : theme.surface0
                            border.width: 1
                            radius: 5
                        }
                        Keys.onReturnPressed: {
                            filterDialog.feedId = model.feedId
                            filterDialog.feedTitle = model.feedTitle || model.feedUrl
                            filterDialog.currentFilter = model.feedFilter
                            filterDialog.open()
                            event.accepted = true
                        }
                        Keys.onLeftPressed: { rowCb.forceActiveFocus(); event.accepted = true }
                        Keys.onRightPressed: { editBtn.forceActiveFocus(); event.accepted = true }
                    }

                    Button {
                        id: editBtn
                        flat: true
                        font.pixelSize: 11
                        implicitHeight: 26
                        implicitWidth: 52
                        onClicked: {
                            editUrlDialog.feedId = model.feedId
                            editUrlDialog.currentUrl = model.feedUrl
                            editUrlDialog.open()
                        }
                        contentItem: Label {
                            text: "Edit"
                            color: theme.blue
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            color: parent.pressed ? theme.surface1
                                 : parent.hovered ? theme.surface0
                                 : "transparent"
                            border.color: (parent.activeFocus || parent.hovered) ? theme.amber : theme.surface0
                            border.width: 1
                            radius: 5
                        }
                        Keys.onReturnPressed: {
                            editUrlDialog.feedId = model.feedId
                            editUrlDialog.currentUrl = model.feedUrl
                            editUrlDialog.open()
                            event.accepted = true
                        }
                        Keys.onLeftPressed: { filterBtn.forceActiveFocus(); event.accepted = true }
                        Keys.onRightPressed: { removeBtn.forceActiveFocus(); event.accepted = true }
                    }

                    Button {
                        id: removeBtn
                        flat: true
                        font.pixelSize: 11
                        implicitHeight: 26
                        implicitWidth: 60
                        onClicked: {
                            root.toggleSelected(model.feedId, true)
                            bulkConfirmDialog.open()
                        }
                        contentItem: Label {
                            text: "Remove"
                            color: theme.red
                            font.pixelSize: 11
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        background: Rectangle {
                            color: parent.pressed ? theme.surface1
                                 : parent.hovered ? theme.surface0
                                 : "transparent"
                            border.color: (parent.activeFocus || parent.hovered) ? theme.amber : theme.surface0
                            border.width: 1
                            radius: 5
                        }
                        Keys.onReturnPressed: {
                            root.toggleSelected(model.feedId, true)
                            bulkConfirmDialog.open()
                            event.accepted = true
                        }
                        Keys.onLeftPressed: { editBtn.forceActiveFocus(); event.accepted = true }
                    }
                }


                Label {
                    text: model.feedDescription
                    color: theme.subtext
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    visible: model.feedDescription !== ""
                }

                Label {
                    text: "Filter: " + model.feedFilter
                    color: theme.blue
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                    visible: model.feedFilter !== ""
                }
            }

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: theme.surface0
                opacity: 0.6
            }

            HoverHandler { id: subItemMouse }

            TapHandler {
                onDoubleTapped: {
                    editUrlDialog.feedId = model.feedId
                    editUrlDialog.currentUrl = model.feedUrl
                    editUrlDialog.open()
                }
            }
        }
    }

    // Edit URL dialog
    Dialog {
        id: editUrlDialog
        title: "Edit Feed URL"
        property int feedId: 0
        property string currentUrl: ""
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 460

        background: Rectangle {
            color: theme.base
            border.color: theme.surface0
            radius: 8
        }

        footer: Rectangle {
            color: theme.mantle
            implicitHeight: 52
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                StyledButton {
                    id: editUrlCancelBtn
                    text: "Cancel"; theme: root.theme; onClicked: editUrlDialog.reject()
                    Keys.onReturnPressed: { editUrlDialog.reject(); event.accepted = true }
                    Keys.onRightPressed: { editUrlOkBtn.forceActiveFocus(); event.accepted = true }
                }
                StyledButton {
                    id: editUrlOkBtn
                    text: "OK"; theme: root.theme; onClicked: editUrlDialog.accept()
                    Keys.onReturnPressed: { editUrlDialog.accept(); event.accepted = true }
                    Keys.onLeftPressed: { editUrlCancelBtn.forceActiveFocus(); event.accepted = true }
                }
            }
        }

        topPadding: 16
        leftPadding: 16
        rightPadding: 16
        bottomPadding: 16

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                text: "Feed URL"
                color: theme.text
                font.bold: true
                Layout.fillWidth: true
            }

            TextField {
                id: editUrlField
                Layout.fillWidth: true
                color: theme.text
                placeholderTextColor: theme.overlay
                font.pixelSize: 13
                background: Rectangle {
                    color: theme.surface1
                    border.color: parent.activeFocus ? theme.blue : theme.overlay
                    border.width: parent.activeFocus ? 2 : 1
                    radius: 6
                }
                leftPadding: 10
                rightPadding: 10
                topPadding: 8
                bottomPadding: 8
                Keys.onReturnPressed: {
                    if (text.trim()) { editUrlDialog.accept(); event.accepted = true }
                }
            }
        }

        onOpened: { editUrlField.text = editUrlDialog.currentUrl; editUrlField.forceActiveFocus() }
        onAccepted: controller.updateFeedUrl(editUrlDialog.feedId, editUrlField.text.trim())
    }

    // Filter dialog
    Dialog {
        id: filterDialog
        title: "Set Filter"
        property int feedId: 0
        property string feedTitle: ""
        property string currentFilter: ""
        modal: true
        anchors.centerIn: Overlay.overlay
        width: 420

        background: Rectangle {
            color: theme.base
            border.color: theme.surface0
            radius: 8
        }

        footer: Rectangle {
            color: theme.mantle
            implicitHeight: 52
            height: 52
            radius: 8
            Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
            Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
            Row {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                StyledButton {
                    id: filterCancelBtn
                    text: "Cancel"; theme: root.theme; onClicked: filterDialog.reject()
                    Keys.onReturnPressed: { filterDialog.reject(); event.accepted = true }
                    Keys.onRightPressed: { filterOkBtn.forceActiveFocus(); event.accepted = true }
                }
                StyledButton {
                    id: filterOkBtn
                    text: "OK"; theme: root.theme; onClicked: filterDialog.accept()
                    Keys.onReturnPressed: { filterDialog.accept(); event.accepted = true }
                    Keys.onLeftPressed: { filterCancelBtn.forceActiveFocus(); event.accepted = true }
                }
            }
        }

        topPadding: 16
        leftPadding: 16
        rightPadding: 16
        bottomPadding: 16

        ListModel { id: filterTermsModel }

        contentItem: ColumnLayout {
            spacing: 12

            Label {
                text: "Filter for: " + filterDialog.feedTitle
                color: theme.text
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ColumnLayout {
                spacing: 4
                Layout.fillWidth: true
                visible: filterTermsModel.count > 0

                Label {
                    text: "Active filters (Space to toggle):"
                    color: theme.subtext
                    font.pixelSize: 11
                    font.bold: true
                }

                Repeater {
                    id: filterTermsRepeater
                    model: filterTermsModel

                    delegate: Rectangle {
                        id: termRow
                        Layout.fillWidth: true
                        height: 30
                        radius: 4
                        color: termMouse.containsMouse ? theme.surface0 : "transparent"
                        border.color: activeFocus ? theme.amber : "transparent"
                        border.width: 1
                        activeFocusOnTab: true

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 6
                            anchors.rightMargin: 6
                            spacing: 8

                            Rectangle {
                                width: 16; height: 16; radius: 3
                                color: model.active ? theme.blue : "transparent"
                                border.color: theme.blue
                                border.width: 2
                                Label {
                                    anchors.centerIn: parent
                                    text: model.active ? "✓" : ""
                                    color: theme.isDark ? "#1e1e2e" : "#ffffff"
                                    font.pixelSize: 11; font.bold: true
                                }
                            }

                            Label {
                                text: model.term
                                color: model.active ? theme.text : theme.overlay
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
                            onClicked: filterTermsModel.setProperty(index, "active", !model.active)
                        }
                        Keys.onSpacePressed: { filterTermsModel.setProperty(index, "active", !model.active); event.accepted = true }
                        Keys.onReturnPressed: { filterTermsModel.setProperty(index, "active", !model.active); event.accepted = true }
                        Keys.onRightPressed: {
                            var next = filterTermsRepeater.itemAt(index + 1)
                            if (next) next.forceActiveFocus(); else filterField.forceActiveFocus()
                            event.accepted = true
                        }
                        Keys.onLeftPressed: {
                            var prev = filterTermsRepeater.itemAt(index - 1)
                            if (prev) prev.forceActiveFocus()
                            event.accepted = true
                        }
                    }
                }
            }

            Label {
                text: filterTermsModel.count > 0 ? "Add another filter term:" : "Enter filter expression:"
                color: theme.subtext
                font.pixelSize: 11
                font.bold: true
            }

            TextField {
                id: filterField
                placeholderText: filterTermsModel.count > 0 ? "e.g. duration:>=300" : "e.g. type:video AND duration:>=300"
                Layout.fillWidth: true
                color: theme.text
                placeholderTextColor: theme.overlay
                font.pixelSize: 13
                background: Rectangle {
                    color: theme.surface1
                    border.color: parent.activeFocus ? theme.blue : theme.overlay
                    border.width: parent.activeFocus ? 2 : 1
                    radius: 6
                }
                leftPadding: 10
                rightPadding: 10
                topPadding: 8
                bottomPadding: 8
                Keys.onReturnPressed: { filterDialog.accept(); event.accepted = true }
            }

            Label {
                text: filterTermsModel.count > 0
                    ? "Deactivate all terms and leave field empty to clear filter"
                    : "Leave empty to remove the filter"
                color: theme.overlay
                font.pixelSize: 11
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }
        }

        onAccepted: {
            var terms = []
            for (var i = 0; i < filterTermsModel.count; i++) {
                var entry = filterTermsModel.get(i)
                if (entry.active) terms.push(entry.term)
            }
            var extra = filterField.text.trim()
            if (extra) terms.push(extra)
            controller.setFilter(filterDialog.feedId, terms.join(" AND "))
        }

        onOpened: {
            filterTermsModel.clear()
            if (filterDialog.currentFilter) {
                var parts = filterDialog.currentFilter.split(" AND ")
                for (var i = 0; i < parts.length; i++) {
                    var t = parts[i].trim()
                    if (t) filterTermsModel.append({ "term": t, "active": true })
                }
            }
            filterField.text = ""
            if (filterTermsModel.count > 0) {
                filterTermsRepeater.itemAt(0).forceActiveFocus()
            } else {
                filterField.forceActiveFocus()
            }
        }
    }
}
