import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One subscription in the manager list: selection checkbox, title, plus the
// Filter, Edit and Remove actions, with the description and active filter
// underneath when there are any.
//
// Extracted from SubscriptionManager.qml, where it was an inline `Component`
// reading `model.*` for its content and opening the manager's dialogs itself.
//
// The five `feed*` properties are `required`, which is what makes the view bind
// them from FeedListModel's roles of the same name. Which dialog opens is the
// caller's business now, because the caller is what owns them.
Rectangle {
    id: row

    // Bound by the view from FeedListModel's roles.
    required property int feedId
    required property string feedUrl
    required property string feedTitle
    required property string feedDescription
    required property string feedFilter

    // Set by the caller.
    required property var theme
    required property bool selected

    signal toggleRequested()
    signal filterRequested()
    signal editRequested()
    signal removeRequested()

    // The row grows by one line for each of the two optional captions.
    readonly property int _baseHeight: 80
    readonly property int _captionHeight: 18

    height: _baseHeight
            + (row.feedFilter !== "" ? _captionHeight : 0)
            + (row.feedDescription !== "" ? _captionHeight : 0)
    color: (row.selected || hover.hovered || row.ListView.isCurrentItem)
           ? theme.mantle : theme.base
    border.color: (hover.hovered || row.ListView.isCurrentItem) ? theme.amber : "transparent"
    border.width: 2

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 8
        anchors.rightMargin: 12
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 4

        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            Rectangle {
                id: checkbox
                objectName: "rowCheckbox"
                width: 18; height: 18; radius: 3
                activeFocusOnTab: true
                color: row.selected ? theme.blue : "transparent"
                border.color: activeFocus ? theme.amber : theme.blue
                border.width: 2
                Label {
                    anchors.centerIn: parent
                    text: row.selected ? "✓" : ""
                    color: theme.isDark ? "#1e1e2e" : "#ffffff"
                    font.pixelSize: 12; font.bold: true
                }
                MouseArea {
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: row.toggleRequested()
                }
                Keys.onSpacePressed: { row.toggleRequested(); event.accepted = true }
                Keys.onReturnPressed: { row.toggleRequested(); event.accepted = true }
                Keys.onRightPressed: { filterAction.forceActiveFocus(); event.accepted = true }
            }

            Label {
                objectName: "rowTitle"
                text: row.feedTitle || row.feedUrl
                color: theme.text
                font.pixelSize: 13
                font.bold: true
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            RowActionButton {
                id: filterAction
                objectName: "filterAction"
                theme: row.theme
                text: "Filter"
                previousItem: checkbox
                nextItem: editAction
                onClicked: row.filterRequested()
            }

            RowActionButton {
                id: editAction
                objectName: "editAction"
                theme: row.theme
                text: "Edit"
                previousItem: filterAction
                nextItem: removeAction
                onClicked: row.editRequested()
            }

            RowActionButton {
                id: removeAction
                objectName: "removeAction"
                theme: row.theme
                text: "Remove"
                labelColour: row.theme.red
                implicitWidth: 60
                previousItem: editAction
                onClicked: row.removeRequested()
            }
        }

        Label {
            text: row.feedDescription
            color: theme.subtext
            font.pixelSize: 11
            elide: Text.ElideRight
            Layout.fillWidth: true
            visible: row.feedDescription !== ""
        }

        Label {
            text: "Filter: " + row.feedFilter
            color: theme.blue
            font.pixelSize: 11
            elide: Text.ElideRight
            Layout.fillWidth: true
            visible: row.feedFilter !== ""
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: theme.surface0
        opacity: 0.6
    }

    HoverHandler { id: hover }

    TapHandler {
        onDoubleTapped: row.editRequested()
    }
}
