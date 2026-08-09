import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One item in the reader's list: thumbnail, title, type chip, date and
// duration, with an unread dot down the left.
//
// Extracted from FeedReader.qml, where it was an inline `Component` reading
// `model.*` and reaching out to the reader for the list, the detail pane and
// the controller.
//
// The `item*` properties are `required`, which is what makes the view bind
// them from ItemListModel's roles of the same name.
//
// `index` has to be declared alongside them: declaring any required property
// stops the view injecting the model's context properties, so an undeclared
// `index` does not exist rather than merely going stale. Reading it throws and
// takes the rest of the handler with it.
Rectangle {
    id: row

    // Bound by the view: its own position, then ItemListModel's roles.
    required property int index
    required property int itemId
    required property string itemTitle
    required property string itemType
    required property string itemUrl
    required property string itemPublished
    required property string itemThumbnail
    required property int itemDuration
    required property bool itemIsRead

    // Set by the caller.
    required property var theme
    required property string durationText

    signal activated()

    // Image.PreserveAspectCrop, named because the number says nothing.
    readonly property int _aspectFill: 2

    height: 84
    color: row.ListView.isCurrentItem ? theme.surface0
         : hover.containsMouse ? theme.surface0 + "80"
         : row.itemIsRead ? "transparent"
         : theme.mantle
    border.color: (hover.containsMouse || row.ListView.isCurrentItem)
                  ? theme.amber : "transparent"
    border.width: 1

    // Unread indicator dot
    Rectangle {
        visible: !row.itemIsRead && !row.ListView.isCurrentItem
        width: 6
        height: 6
        radius: 3
        color: theme.blue
        anchors.left: parent.left
        anchors.leftMargin: 6
        anchors.verticalCenter: parent.verticalCenter
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 12
        anchors.topMargin: 10
        anchors.bottomMargin: 10
        spacing: 10

        Item {
            Layout.preferredWidth: 56
            Layout.maximumWidth: 56
            Layout.preferredHeight: 56
            Layout.maximumHeight: 56
            Layout.alignment: Qt.AlignVCenter
            visible: row.itemThumbnail !== ""
            clip: true

            Image {
                anchors.centerIn: parent
                source: row.itemThumbnail
                width: 56
                height: 56
                fillMode: row._aspectFill
            }

            Rectangle {
                anchors.fill: parent
                color: "transparent"
                border.color: theme.surface0
                border.width: 1
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 5

            Label {
                objectName: "itemTitleLabel"
                text: row.itemTitle
                color: row.itemIsRead ? theme.subtext : theme.text
                font.pixelSize: 13
                font.bold: !row.itemIsRead
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                Layout.fillWidth: true
            }

            RowLayout {
                spacing: 6

                Rectangle {
                    height: 18
                    Layout.preferredWidth: typeChip.implicitWidth + 10
                    radius: 3
                    color: theme.surface0

                    Label {
                        id: typeChip
                        anchors.centerIn: parent
                        text: row.itemType
                        color: theme.blue
                        font.pixelSize: 10
                    }
                }

                Label {
                    text: row.itemPublished.substring(0, 10)
                    color: theme.overlay
                    font.pixelSize: 10
                }

                Label {
                    text: row.durationText
                    color: theme.overlay
                    font.pixelSize: 10
                    visible: row.itemDuration > 0
                }
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: theme.surface0
        opacity: 0.5
        visible: !(hover.containsMouse || row.ListView.isCurrentItem)
    }

    MouseArea {
        id: hover
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: row.activated()
    }
}
