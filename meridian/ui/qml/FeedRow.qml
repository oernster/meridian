import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One feed in the sidebar list: selection checkbox, icon, title with source
// type, plus the unread badge.
//
// Extracted from main.qml, where it was an inline `Component` reading `model.*`
// for its content and reaching out to the window for the selection, the
// controller and the context popup.
//
// The six `feed*` properties are `required`, which is what makes the view bind
// them from FeedListModel's roles of the same name. Current-row styling comes
// from the attached ListView property rather than a comparison against the
// view's currentIndex, so the row does not need to know its own index.
Rectangle {
    id: row

    // Bound by the view from FeedListModel's roles.
    required property int feedId
    required property string feedUrl
    required property string feedTitle
    required property string feedIcon
    required property string feedSourceType
    required property int feedUnreadCount

    // Set by the caller.
    required property var theme
    required property bool selected

    signal toggleRequested()
    signal activated()
    signal contextMenuRequested(real globalX, real globalY)

    height: 64
    color: row.ListView.isCurrentItem ? theme.surface0 : "transparent"
    border.color: (rowMouse.containsMouse || row.ListView.isCurrentItem)
                  ? theme.amber : "transparent"
    border.width: 1

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onPressed: function(mouse) {
            if (mouse.button === Qt.RightButton) {
                mouse.accepted = true
                var gp = row.mapToGlobal(mouse.x, mouse.y)
                row.contextMenuRequested(gp.x, gp.y)
            }
        }
        onClicked: function(mouse) {
            if (mouse.button === Qt.LeftButton) row.activated()
        }
    }

    Rectangle {
        visible: row.ListView.isCurrentItem
        width: 3; height: 40; radius: 2
        color: theme.blue
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8; anchors.rightMargin: 12
        anchors.topMargin: 8; anchors.bottomMargin: 8
        spacing: 8
        z: 1

        Rectangle {
            width: 22; height: 22; radius: 3
            color: row.selected ? theme.blue : "transparent"
            border.color: theme.blue; border.width: 2
            Label {
                anchors.centerIn: parent
                text: row.selected ? "✓" : ""
                color: theme.isDark ? "#1e1e2e" : "#ffffff"
                font.pixelSize: 12; font.bold: true
            }
            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: Qt.PointingHandCursor
                onClicked: row.toggleRequested()
            }
        }

        Item {
            Layout.preferredWidth: 36
            Layout.preferredHeight: 36
            Layout.minimumWidth: 36
            Layout.minimumHeight: 36
            Layout.maximumWidth: 36
            Layout.maximumHeight: 36

            Rectangle {
                width: 36; height: 36; radius: 8
                color: theme.surface0
                visible: row.feedIcon === ""
                Label {
                    anchors.centerIn: parent
                    text: (row.feedTitle || row.feedUrl).charAt(0).toUpperCase()
                    color: theme.blue; font.pixelSize: 15; font.bold: true
                }
            }
            Image {
                width: 36; height: 36
                source: row.feedIcon
                sourceSize: Qt.size(36, 36)
                fillMode: Image.PreserveAspectFit
                visible: row.feedIcon !== ""
            }
        }

        ColumnLayout {
            Layout.fillWidth: true; spacing: 4
            Label {
                objectName: "feedTitleLabel"
                text: row.feedTitle || row.feedUrl
                color: theme.text; font.pixelSize: 13
                elide: Text.ElideRight; Layout.fillWidth: true
            }
            Label {
                text: row.feedSourceType.toUpperCase()
                color: theme.blue; font.pixelSize: 10; font.bold: true
            }
        }

        Rectangle {
            visible: row.feedUnreadCount > 0
            width: Math.max(badge.contentWidth + 14, 24); height: 22; radius: 11
            color: theme.blue
            Label {
                id: badge
                objectName: "unreadBadge"
                anchors.centerIn: parent
                text: row.feedUnreadCount > 99 ? "99+" : row.feedUnreadCount
                color: theme.isDark ? "#1e1e2e" : "#ffffff"
                font.pixelSize: 11; font.bold: true
            }
        }
    }
}
