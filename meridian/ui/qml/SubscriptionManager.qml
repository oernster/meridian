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
                }


                Rectangle {
                    Layout.fillWidth: true
                    height: 38
                    radius: 8
                    color: subscribeBtn.pressed ? theme.blue + "cc"
                         : urlField.text.trim().startsWith("https://") ? (subscribeBtn.containsMouse ? theme.blue + "dd" : theme.blue)
                         : theme.surface1
                    opacity: urlField.text.trim().startsWith("https://") ? 1.0 : 0.5
                    border.color: subscribeBtn.containsMouse && urlField.text.trim().startsWith("https://") ? theme.amber : "transparent"
                    border.width: 1

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
                    width: 18; height: 18; radius: 3
                    color: (root.selectedCount > 0) ? theme.blue : "transparent"
                    border.color: theme.blue; border.width: 2
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
                    visible: root.selectedCount > 0
                    height: 26
                    width: removeSelLbl.contentWidth + 16
                    radius: 5
                    color: removeSelMouse.containsMouse ? theme.surface0 : "transparent"
                    border.color: theme.red
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
        }
    }

    Dialog {
        id: bulkConfirmDialog
        title: "Remove Subscriptions"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        background: Rectangle { color: theme.base; border.color: theme.surface0; radius: 8 }
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
            height: 80
            color: (!!root.selectedIds[model.feedId] || subItemMouse.hovered) ? theme.mantle : theme.base
            border.color: subItemMouse.hovered ? theme.amber : "transparent"
            border.width: 1

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
                        width: 18; height: 18; radius: 3
                        color: !!root.selectedIds[model.feedId] ? theme.blue : "transparent"
                        border.color: theme.blue; border.width: 2
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
                        flat: true
                        font.pixelSize: 11
                        implicitHeight: 26
                        implicitWidth: 52
                        onClicked: {
                            filterDialog.feedId = model.feedId
                            filterDialog.feedTitle = model.feedTitle || model.feedUrl
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
                            border.color: parent.hovered ? theme.amber : theme.surface0
                            border.width: 1
                            radius: 5
                        }
                    }

                    Button {
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
                            border.color: parent.hovered ? theme.amber : theme.surface0
                            border.width: 1
                            radius: 5
                        }
                    }
                }


                Label {
                    text: model.feedUrl
                    color: theme.subtext
                    font.pixelSize: 11
                    elide: Text.ElideRight
                    Layout.fillWidth: true
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
        }
    }

    // Filter dialog
    Dialog {
        id: filterDialog
        title: "Set Filter"
        property int feedId: 0
        property string feedTitle: ""
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: Overlay.overlay
        width: 420

        background: Rectangle {
            color: theme.base
            border.color: theme.surface0
            radius: 8
        }

        ColumnLayout {
            width: 380
            spacing: 12

            Label {
                text: "Filter for: " + filterDialog.feedTitle
                color: theme.text
                font.bold: true
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            TextField {
                id: filterField
                placeholderText: "e.g. type:video AND duration:>=300"
                Layout.fillWidth: true
                color: theme.text
                placeholderTextColor: theme.overlay
                font.pixelSize: 13
                background: Rectangle {
                    color: theme.surface0
                    border.color: parent.activeFocus ? theme.blue : theme.surface1
                    border.width: parent.activeFocus ? 2 : 1
                    radius: 6
                }
                leftPadding: 10
                rightPadding: 10
                topPadding: 8
                bottomPadding: 8
            }

            Label {
                text: "Leave empty to remove the filter"
                color: theme.overlay
                font.pixelSize: 11
            }
        }

        onAccepted: controller.setFilter(filterDialog.feedId, filterField.text)
        onOpened: filterField.text = ""
    }
}
