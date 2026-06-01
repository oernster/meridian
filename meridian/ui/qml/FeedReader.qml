import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

Item {
    id: root
    required property var theme
    readonly property int _aspectFill: Image.PreserveAspectFill

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Item list panel
        Rectangle {
            Layout.preferredWidth: 360
            Layout.fillHeight: true
            color: theme.mantle

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                // Panel header
                Rectangle {
                    Layout.fillWidth: true
                    height: 48
                    color: theme.mantle

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 8

                        Label {
                            text: "Items"
                            font.pixelSize: 14
                            font.bold: true
                            color: theme.text
                            Layout.fillWidth: true
                        }

                        Button {
                            flat: true
                            font.pixelSize: 11
                            implicitHeight: 30
                            onClicked: {
                                if (controller.selectedFeedId > 0)
                                    controller.markAllRead(controller.selectedFeedId)
                            }
                            contentItem: Label {
                                text: "Mark all read"
                                color: theme.subtext
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                            background: Rectangle {
                                color: parent.pressed ? theme.surface1
                                     : parent.hovered ? theme.surface0
                                     : "transparent"
                                radius: 5
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

                ListView {
                    id: itemList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: controller ? controller.itemModel : null
                    delegate: itemDelegate
                    currentIndex: -1
                    ScrollBar.vertical: ScrollBar { }
                }
            }
        }

        // Divider
        Rectangle {
            width: 1
            Layout.fillHeight: true
            color: theme.surface0
        }

        // Detail pane
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: theme.base

            // Empty state
            ColumnLayout {
                anchors.centerIn: parent
                spacing: 12
                visible: detailTitle.text === ""

                Label {
                    text: "📰"
                    font.pixelSize: 48
                    Layout.alignment: Qt.AlignHCenter
                }
                Label {
                    text: "Select a feed and item to read"
                    color: theme.overlay
                    font.pixelSize: 15
                    Layout.alignment: Qt.AlignHCenter
                }
            }

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 14
                visible: detailTitle.text !== ""

                Label {
                    id: detailTitle
                    text: ""
                    color: theme.text
                    font.pixelSize: 20
                    font.bold: true
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                RowLayout {
                    spacing: 8

                    Rectangle {
                        height: 22
                        width: typeLabel.contentWidth + 14
                        radius: 4
                        color: theme.surface0

                        Label {
                            id: typeLabel
                            anchors.centerIn: parent
                            text: detailTypeStor.text.toUpperCase()
                            color: theme.blue
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 0.8
                        }
                    }

                    Label {
                        id: detailMeta
                        text: ""
                        color: theme.subtext
                        font.pixelSize: 12
                    }
                }

                // Media player
                Rectangle {
                    id: playerContainer
                    visible: false
                    Layout.fillWidth: true
                    height: Math.min(root.height * 0.38, 340)
                    color: "#000"
                    radius: 10

                    MediaPlayer {
                        id: mediaPlayer
                        videoOutput: videoOutput
                    }

                    VideoOutput {
                        id: videoOutput
                        anchors.fill: parent
                        anchors.bottomMargin: 48
                    }

                    // Audio-only visual
                    Rectangle {
                        anchors.fill: parent
                        anchors.bottomMargin: 48
                        color: theme.mantle
                        visible: detailTypeStor.text === "audio" || detailTypeStor.text === "podcast"
                        radius: 10

                        Label {
                            anchors.centerIn: parent
                            text: "🎵"
                            font.pixelSize: 40
                        }
                    }

                    // Controls bar
                    Rectangle {
                        anchors.bottom: parent.bottom
                        width: parent.width
                        height: 48
                        color: theme.mantle
                        radius: 10
                        Rectangle {
                            anchors.top: parent.top
                            width: parent.width
                            height: 10
                            color: theme.mantle
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 8

                            Button {
                                flat: true
                                font.pixelSize: 16
                                text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                                implicitWidth: 36
                                implicitHeight: 36
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
                                color: theme.subtext
                                font.pixelSize: 10
                            }
                        }
                    }
                }

                Label { id: detailTypeStor; visible: false; text: "" }

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
                        color: theme.text
                        background: null
                        textFormat: Text.RichText
                        font.pixelSize: 14
                        onLinkActivated: (link) => Qt.openUrlExternally(link)
                    }
                }

                Rectangle {
                    height: 36
                    width: openBtn.contentWidth + 32
                    radius: 8
                    color: openBtn.pressed ? theme.blue + "cc"
                         : openBtn.containsMouse ? theme.blue
                         : theme.surface0

                    Label {
                        id: openBtn
                        anchors.centerIn: parent
                        text: "Open in Browser →"
                        color: openBtn.containsMouse ? (theme.isDark ? "#1e1e2e" : "#ffffff")
                             : theme.text
                        font.pixelSize: 13
                        property bool pressed: false
                        property bool containsMouse: false
                    }

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onEntered: openBtn.containsMouse = true
                        onExited:  openBtn.containsMouse = false
                        onPressed: openBtn.pressed = true
                        onReleased: openBtn.pressed = false
                        onClicked: Qt.openUrlExternally(detailUrl.text)
                    }
                }

                Label { id: detailUrl; visible: false; text: "" }
            }
        }
    }

    // Item delegate
    Component {
        id: itemDelegate

        Rectangle {
            width: itemList.width
            height: 84
            color: itemList.currentIndex === index
                ? theme.surface0
                : itemMouse.containsMouse ? theme.surface0 + "80"
                : model.itemIsRead ? "transparent"
                : theme.mantle

            // Unread indicator dot
            Rectangle {
                visible: !model.itemIsRead && itemList.currentIndex !== index
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
                    visible: model.itemThumbnail !== ""
                    clip: true

                    Image {
                        anchors.centerIn: parent
                        source: model.itemThumbnail
                        width: 56
                        height: 56
                        fillMode: root._aspectFill
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
                        text: model.itemTitle
                        color: model.itemIsRead ? theme.subtext : theme.text
                        font.pixelSize: 13
                        font.bold: !model.itemIsRead
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        spacing: 6

                        Rectangle {
                            height: 18
                            width: typeChip.contentWidth + 10
                            radius: 3
                            color: theme.surface0

                            Label {
                                id: typeChip
                                anchors.centerIn: parent
                                text: model.itemType
                                color: theme.blue
                                font.pixelSize: 10
                            }
                        }

                        Label {
                            text: model.itemPublished.substring(0, 10)
                            color: theme.overlay
                            font.pixelSize: 10
                        }

                        Label {
                            text: model.itemDuration > 0 ? _formatTime(model.itemDuration * 1000) : ""
                            color: theme.overlay
                            font.pixelSize: 10
                            visible: model.itemDuration > 0
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
            }

            MouseArea {
                id: itemMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    itemList.currentIndex = index
                    console.log("Item clicked title:", model.itemTitle, "id:", model.itemId)
                    _loadItem({
                        itemTitle:       model.itemTitle,
                        itemPublished:   model.itemPublished,
                        itemType:        model.itemType,
                        itemDescription: model.itemDescription,
                        itemUrl:         model.itemUrl,
                        itemMediaUrl:    model.itemMediaUrl,
                        itemThumbnail:   model.itemThumbnail
                    })
                    controller.markRead(model.itemId)
                }
            }
        }
    }

    function _loadItem(item) {
        console.log("_loadItem called, title:", item.itemTitle, "desc length:", item.itemDescription ? item.itemDescription.length : "null")
        detailTitle.text = item.itemTitle
        detailMeta.text = item.itemPublished.substring(0, 16).replace("T", "  ")
        detailTypeStor.text = item.itemType
        detailDescription.text = item.itemDescription
        detailUrl.text = item.itemUrl
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
