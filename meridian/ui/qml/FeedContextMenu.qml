import QtQuick
import QtQuick.Controls

// The sidebar's right-click menu: remove this feed, plus remove the selection
// when there is one.
//
// Extracted from main.qml. It carries the feed it was opened on so the caller
// can read it back when an entry is chosen; it closes itself before
// reporting, since both entries lead to a confirmation that would otherwise
// open underneath it.
Popup {
    id: menu

    required property var theme
    required property int selectedCount

    property int targetFeedId: 0
    property string targetTitle: ""

    signal removeRequested()
    signal removeSelectedRequested()

    readonly property int _entryHeight: 36
    readonly property int _padding: 4

    parent: Overlay.overlay
    padding: _padding
    width: 180
    height: menu.selectedCount > 0
            ? (_entryHeight * 2 + _padding * 2)
            : (_entryHeight + _padding * 2)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // Opens at a position given in global coordinates, which is what a mouse
    // event on a row reports.
    function openAt(globalX, globalY) {
        var local = Overlay.overlay.mapFromGlobal(globalX, globalY)
        menu.x = local.x
        menu.y = local.y
        menu.open()
    }

    background: Rectangle {
        color: theme.mantle
        border.color: theme.surface0
        border.width: 1
        radius: 6
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            objectName: "removeEntry"
            width: parent.width; height: menu._entryHeight
            radius: 4
            color: removeHover.containsMouse ? theme.surface0 : "transparent"
            Label {
                anchors.centerIn: parent
                text: "Remove Feed"
                color: theme.red
                font.pixelSize: 13
                font.bold: true
            }
            MouseArea {
                id: removeHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    menu.close()
                    menu.removeRequested()
                }
            }
        }

        Rectangle {
            objectName: "removeSelectedEntry"
            visible: menu.selectedCount > 0
            width: parent.width; height: menu._entryHeight
            radius: 4
            color: removeSelectedHover.containsMouse ? theme.surface0 : "transparent"
            Label {
                anchors.centerIn: parent
                text: "Remove " + menu.selectedCount + " selected"
                color: theme.red
                font.pixelSize: 13
                font.bold: true
            }
            MouseArea {
                id: removeSelectedHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    menu.close()
                    menu.removeSelectedRequested()
                }
            }
        }
    }
}
