import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    title: "Meridian"
    width: 1200
    height: 750
    minimumWidth: 800
    minimumHeight: 500
    visible: true

    Component.onCompleted: controller.loadFeeds()

    Connections {
        target: controller
        function onErrorOccurred(msg) {
            errorDialog.message = msg
            errorDialog.open()
        }
        function onNewItemsAvailable(feedId, count) {
            // Feed model already refreshed by controller; no UI action needed here
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Left sidebar: feed list + subscription manager button
        Rectangle {
            id: sidebar
            Layout.preferredWidth: 260
            Layout.fillHeight: true
            color: "#1e1e2e"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 4

                Label {
                    text: "Meridian"
                    font.pixelSize: 18
                    font.bold: true
                    color: "#cdd6f4"
                    Layout.topMargin: 8
                    Layout.bottomMargin: 4
                }

                ListView {
                    id: feedList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: controller.feedModel
                    delegate: feedDelegate
                    currentIndex: -1
                }

                Button {
                    text: "Manage Subscriptions"
                    Layout.fillWidth: true
                    onClicked: subManagerDrawer.open()
                }
            }
        }

        // Main content area
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#181825"

            FeedReader {
                anchors.fill: parent
                controller: controller
            }
        }
    }

    Component {
        id: feedDelegate
        Rectangle {
            width: feedList.width
            height: 56
            color: feedList.currentIndex === index ? "#313244" : "transparent"
            radius: 6

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Image {
                    source: model.feedIcon
                    width: 24
                    height: 24
                    fillMode: Image.PreserveAspectFit
                    visible: model.feedIcon !== ""
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: model.feedTitle
                        color: "#cdd6f4"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Label {
                        text: model.feedSourceType
                        color: "#6c7086"
                        font.pixelSize: 10
                    }
                }

                Rectangle {
                    visible: model.feedUnreadCount > 0
                    width: unreadLabel.width + 10
                    height: 18
                    radius: 9
                    color: "#89b4fa"

                    Label {
                        id: unreadLabel
                        anchors.centerIn: parent
                        text: model.feedUnreadCount
                        color: "#1e1e2e"
                        font.pixelSize: 10
                        font.bold: true
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    feedList.currentIndex = index
                    controller.selectFeed(model.feedId)
                }
            }
        }
    }

    Drawer {
        id: subManagerDrawer
        width: Math.min(500, root.width * 0.45)
        height: root.height
        edge: Qt.RightEdge

        SubscriptionManager {
            anchors.fill: parent
            controller: controller
            onClose: subManagerDrawer.close()
        }
    }

    Dialog {
        id: errorDialog
        title: "Error"
        property string message: ""
        standardButtons: Dialog.Ok
        anchors.centerIn: parent
        Label { text: errorDialog.message }
    }
}
