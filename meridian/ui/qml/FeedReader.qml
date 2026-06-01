import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

Item {
    id: root
    required property var controller

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Item list
        Rectangle {
            Layout.preferredWidth: 340
            Layout.fillHeight: true
            color: "#181825"
            border.color: "#313244"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.margins: 8

                    Label {
                        text: "Items"
                        color: "#cdd6f4"
                        font.pixelSize: 14
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "Mark All Read"
                        flat: true
                        font.pixelSize: 11
                        onClicked: {
                            if (controller.selectedFeedId > 0)
                                controller.markAllRead(controller.selectedFeedId)
                        }
                    }
                }

                ListView {
                    id: itemList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: controller.itemModel
                    delegate: itemDelegate
                    currentIndex: -1
                }
            }
        }

        // Detail / player pane
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#11111b"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                visible: detailTitle.text !== ""

                Label {
                    id: detailTitle
                    text: ""
                    color: "#cdd6f4"
                    font.pixelSize: 20
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Label {
                    id: detailMeta
                    text: ""
                    color: "#6c7086"
                    font.pixelSize: 11
                    Layout.fillWidth: true
                }

                // Inline media player (video/audio/short/livestream)
                Rectangle {
                    id: playerContainer
                    visible: false
                    Layout.fillWidth: true
                    height: Math.min(root.height * 0.4, 360)
                    color: "#000"
                    radius: 8

                    MediaPlayer {
                        id: mediaPlayer
                        videoOutput: videoOutput
                    }

                    VideoOutput {
                        id: videoOutput
                        anchors.fill: parent
                    }

                    // Audio-only fallback visual
                    Rectangle {
                        anchors.fill: parent
                        color: "#1e1e2e"
                        visible: detailType.text === "audio" || detailType.text === "podcast"
                        radius: 8

                        Label {
                            anchors.centerIn: parent
                            text: "Audio"
                            color: "#89b4fa"
                            font.pixelSize: 24
                        }
                    }

                    RowLayout {
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: 8

                        Button {
                            text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "Pause" : "Play"
                            onClicked: {
                                if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                                    mediaPlayer.pause()
                                else
                                    mediaPlayer.play()
                            }
                        }

                        Slider {
                            Layout.fillWidth: true
                            from: 0
                            to: mediaPlayer.duration > 0 ? mediaPlayer.duration : 1
                            value: mediaPlayer.position
                            onMoved: mediaPlayer.position = value
                        }

                        Label {
                            text: _formatTime(mediaPlayer.position) + " / " + _formatTime(mediaPlayer.duration)
                            color: "#cdd6f4"
                            font.pixelSize: 10
                        }
                    }
                }

                Label { id: detailType; visible: false; text: "" }

                // Thumbnail for non-media items
                Image {
                    id: detailThumbnail
                    visible: !playerContainer.visible && source.toString() !== ""
                    Layout.fillWidth: true
                    height: 200
                    fillMode: Image.PreserveAspectFit
                }

                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    TextArea {
                        id: detailDescription
                        readOnly: true
                        wrapMode: Text.WordWrap
                        color: "#cdd6f4"
                        background: null
                        textFormat: Text.RichText
                        onLinkActivated: (link) => Qt.openUrlExternally(link)
                    }
                }

                RowLayout {
                    Button {
                        text: "Open in Browser"
                        onClicked: Qt.openUrlExternally(detailUrl.text)
                    }
                    Label { id: detailUrl; visible: false; text: "" }
                }
            }

            Label {
                anchors.centerIn: parent
                text: "Select a feed and item to read"
                color: "#6c7086"
                font.pixelSize: 16
                visible: detailTitle.text === ""
            }
        }
    }

    Component {
        id: itemDelegate
        Rectangle {
            width: itemList.width
            height: 72
            color: itemList.currentIndex === index
                ? "#313244"
                : (model.itemIsRead ? "transparent" : "#1e1e2e")
            radius: 4

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                Image {
                    source: model.itemThumbnail
                    width: 48
                    height: 48
                    fillMode: Image.PreserveAspectFill
                    visible: model.itemThumbnail !== ""
                    layer.enabled: true
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Label {
                        text: model.itemTitle
                        color: model.itemIsRead ? "#6c7086" : "#cdd6f4"
                        font.pixelSize: 12
                        font.bold: !model.itemIsRead
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Label {
                            text: model.itemType
                            color: "#89b4fa"
                            font.pixelSize: 10
                        }
                        Label {
                            text: model.itemPublished.substring(0, 10)
                            color: "#6c7086"
                            font.pixelSize: 10
                        }
                        Label {
                            text: model.itemDuration > 0 ? _formatTime(model.itemDuration * 1000) : ""
                            color: "#6c7086"
                            font.pixelSize: 10
                            visible: model.itemDuration > 0
                        }
                    }
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    itemList.currentIndex = index
                    _loadItem(model)
                    controller.markRead(model.itemId)
                }
            }
        }
    }

    function _loadItem(item) {
        detailTitle.text = item.itemTitle
        detailMeta.text = item.itemType + " · " + item.itemPublished.substring(0, 16).replace("T", " ")
        detailDescription.text = item.itemDescription
        detailUrl.text = item.itemUrl
        detailType.text = item.itemType
        const isMedia = ["video", "audio", "short", "livestream"].includes(item.itemType)
        playerContainer.visible = isMedia && item.itemMediaUrl !== ""
        if (isMedia && item.itemMediaUrl !== "") {
            mediaPlayer.source = item.itemMediaUrl
        } else {
            mediaPlayer.source = ""
        }
        detailThumbnail.source = item.itemThumbnail || ""
    }

    function _formatTime(ms) {
        const s = Math.floor(ms / 1000)
        const h = Math.floor(s / 3600)
        const m = Math.floor((s % 3600) / 60)
        const sec = s % 60
        if (h > 0)
            return h + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
        return String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
    }
}
