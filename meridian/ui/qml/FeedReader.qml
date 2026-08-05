import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import QtWebEngine
import Qt.labs.settings

Item {
    id: root
    required property var theme
    readonly property int _aspectFill: 2
    property var firstHeaderBtn: null
    readonly property var lastFocusItem: openBtnRect

    Settings {
        id: appSettings
        category: "Player"
        property real volume: 0.2
    }

    Connections {
        target: controller
        function onItemsChanged() {
            if (controller.itemModel.rowCount() === 0) {
                detailTitle.text = ""
                detailMeta.text = ""
                detailTypeStor.text = ""
                detailDescription.text = ""
                detailUrl.text = ""
                detailThumbnail.source = ""
                playerContainer.visible = false
                mediaPlayer.source = ""
            }
        }
    }

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
                    id: itemsHeader
                    Layout.fillWidth: true
                    height: 48
                    color: theme.mantle

                    property string _itemSort: "newest"

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

                        Row {
                            spacing: 4
                            Repeater {
                                id: itemSortRepeater
                                model: [
                                    { key: "newest", label: "Newest" },
                                    { key: "oldest", label: "Oldest" },
                                    { key: "alpha",  label: "A→Z"    }
                                ]
                                delegate: Rectangle {
                                    property bool isActive: itemsHeader._itemSort === modelData.key
                                    property bool _hov: false
                                    height: 26; radius: 4
                                    implicitWidth: _il.implicitWidth + 12
                                    activeFocusOnTab: !isActive
                                    color: isActive ? theme.surface0 : "transparent"
                                    border.color: isActive ? theme.blue : (_hov || activeFocus) ? theme.amber : "transparent"
                                    border.width: activeFocus ? 2 : 1
                                    Label {
                                        id: _il
                                        anchors.centerIn: parent
                                        text: modelData.label
                                        color: parent.isActive ? theme.blue : (parent._hov || parent.activeFocus) ? theme.text : theme.overlay
                                        font.pixelSize: 10; font.bold: parent.isActive
                                    }
                                    HoverHandler { onHoveredChanged: parent._hov = hovered }
                                    MouseArea {
                                        anchors.fill: parent
                                        enabled: !parent.isActive
                                        cursorShape: parent.isActive ? Qt.ArrowCursor : Qt.PointingHandCursor
                                        onClicked: {
                                            itemsHeader._itemSort = modelData.key
                                            controller.setItemSort(modelData.key)
                                        }
                                    }
                                    Keys.onReturnPressed: { if (!isActive) { itemsHeader._itemSort = modelData.key; controller.setItemSort(modelData.key) } }
                                    Keys.onPressed: function(event) {
                                        if (event.key === Qt.Key_Space && !isActive) {
                                            itemsHeader._itemSort = modelData.key
                                            controller.setItemSort(modelData.key)
                                            event.accepted = true
                                        }
                                    }
                                    Keys.onTabPressed: {
                                        event.accepted = true
                                        var found = false
                                        for (var i = index + 1; i < itemSortRepeater.count; i++) {
                                            var it = itemSortRepeater.itemAt(i)
                                            if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                        }
                                        if (!found) markAllReadBtn.forceActiveFocus(Qt.TabFocusReason)
                                    }
                                    Keys.onBacktabPressed: {
                                        event.accepted = true
                                        var found = false
                                        for (var i = index - 1; i >= 0; i--) {
                                            var it = itemSortRepeater.itemAt(i)
                                            if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                        }
                                        if (!found) {
                                            var prev = nextItemInFocusChain(false)
                                            if (prev && prev !== this) prev.forceActiveFocus(Qt.BacktabFocusReason)
                                        }
                                    }
                                    Keys.onRightPressed: {
                                        event.accepted = true
                                        var found = false
                                        for (var i = index + 1; i < itemSortRepeater.count; i++) {
                                            var it = itemSortRepeater.itemAt(i)
                                            if (it && !it.isActive) { it.forceActiveFocus(Qt.TabFocusReason); found = true; break }
                                        }
                                        if (!found) markAllReadBtn.forceActiveFocus(Qt.TabFocusReason)
                                    }
                                    Keys.onLeftPressed: {
                                        event.accepted = true
                                        var found = false
                                        for (var i = index - 1; i >= 0; i--) {
                                            var it = itemSortRepeater.itemAt(i)
                                            if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                        }
                                        if (!found) {
                                            var prev = nextItemInFocusChain(false)
                                            if (prev && prev !== this) prev.forceActiveFocus(Qt.BacktabFocusReason)
                                        }
                                    }
                                }
                            }
                        }

                        Button {
                            id: markAllReadBtn
                            flat: true
                            font.pixelSize: 11
                            implicitHeight: 30
                            activeFocusOnTab: true
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
                                border.color: (parent.hovered || parent.activeFocus) ? theme.amber : "transparent"
                                border.width: 1
                                radius: 5
                            }
                            Keys.onTabPressed:     { event.accepted = true; itemList.forceActiveFocus(Qt.TabFocusReason) }
                            Keys.onRightPressed:   { event.accepted = true; itemList.forceActiveFocus(Qt.TabFocusReason) }
                            Keys.onBacktabPressed: {
                                event.accepted = true
                                var found = false
                                for (var i = itemSortRepeater.count - 1; i >= 0; i--) {
                                    var it = itemSortRepeater.itemAt(i)
                                    if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                }
                                if (!found) {
                                    var prev = markAllReadBtn.nextItemInFocusChain(false)
                                    if (prev && prev !== markAllReadBtn) prev.forceActiveFocus(Qt.BacktabFocusReason)
                                }
                            }
                            Keys.onLeftPressed: {
                                event.accepted = true
                                var found = false
                                for (var i = itemSortRepeater.count - 1; i >= 0; i--) {
                                    var it = itemSortRepeater.itemAt(i)
                                    if (it && !it.isActive) { it.forceActiveFocus(Qt.BacktabFocusReason); found = true; break }
                                }
                                if (!found) {
                                    var prev = markAllReadBtn.nextItemInFocusChain(false)
                                    if (prev && prev !== markAllReadBtn) prev.forceActiveFocus(Qt.BacktabFocusReason)
                                }
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
                    activeFocusOnTab: true
                    keyNavigationEnabled: true
                    ScrollBar.vertical: ScrollBar { id: itemVScroll; policy: ScrollBar.AlwaysOn }
                    onActiveFocusChanged: {
                        if (activeFocus && currentIndex < 0 && count > 0)
                            currentIndex = 0
                    }
                    onCurrentIndexChanged: {
                        if (activeFocus && currentIndex >= 0) {
                            var m = controller.itemModel
                            var mi = m.index(currentIndex, 0)
                            var itemId = m.data(mi, Qt.UserRole)
                            _loadItem({
                                itemTitle:       m.data(mi, Qt.UserRole + 1),
                                itemPublished:   m.data(mi, Qt.UserRole + 4),
                                itemType:        m.data(mi, Qt.UserRole + 2),
                                itemDescription: m.data(mi, Qt.UserRole + 8),
                                itemUrl:         m.data(mi, Qt.UserRole + 3),
                                itemMediaUrl:    m.data(mi, Qt.UserRole + 10),
                                itemThumbnail:   m.data(mi, Qt.UserRole + 5)
                            })
                            controller.markRead(itemId)
                        }
                    }
                    Keys.onTabPressed: {
                        event.accepted = true
                        if (playerContainer.visible && !playerContainer.isYoutube)
                            playPauseBtn.forceActiveFocus(Qt.TabFocusReason)
                        else
                            openBtnRect.forceActiveFocus(Qt.TabFocusReason)
                    }
                    Keys.onRightPressed: {
                        event.accepted = true
                        if (playerContainer.visible && !playerContainer.isYoutube)
                            playPauseBtn.forceActiveFocus(Qt.TabFocusReason)
                        else
                            openBtnRect.forceActiveFocus(Qt.TabFocusReason)
                    }
                    Keys.onBacktabPressed: { event.accepted = true; markAllReadBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                    Keys.onLeftPressed:    { event.accepted = true; markAllReadBtn.forceActiveFocus(Qt.BacktabFocusReason) }
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

            // Hidden state storage (outside ColumnLayout so it persists)
            Label { id: detailTypeStor; visible: false; text: "" }
            Label { id: detailUrl;      visible: false; text: "" }

            ScrollView {
                id: detailScroll
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: openBtnRect.top
                anchors.bottomMargin: 8
                clip: true
                contentWidth: availableWidth
                visible: detailTitle.text !== ""

                ColumnLayout {
                    width: parent.width
                    spacing: 0

                    // Hero thumbnail: full width, fixed height, crop-fill
                    Image {
                        id: detailThumbnail
                        visible: source.toString() !== "" && !playerContainer.visible
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        Layout.maximumHeight: 360
                        fillMode: Image.PreserveAspectFit
                        clip: false
                    }

                    // Media player (video/audio/YouTube embed)
                    Rectangle {
                        id: playerContainer
                        visible: false
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(root.height * 0.38, 340)
                        color: "#000"
                        radius: 0

                        property bool isYoutube: false

                        MediaPlayer {
                            id: mediaPlayer
                            videoOutput: videoOutput
                            audioOutput: audioOutput
                        }

                        AudioOutput {
                            id: audioOutput
                            Component.onCompleted: volume = appSettings.volume
                        }

                        VideoOutput {
                            id: videoOutput
                            anchors.fill: parent
                            anchors.bottomMargin: 48
                            visible: !playerContainer.isYoutube
                        }

                        WebEngineView {
                            id: youtubeView
                            anchors.fill: parent
                            anchors.bottomMargin: 0
                            visible: playerContainer.isYoutube
                        }

                        Rectangle {
                            anchors.fill: parent
                            anchors.bottomMargin: 48
                            color: theme.mantle
                            visible: !playerContainer.isYoutube && (detailTypeStor.text === "audio" || detailTypeStor.text === "podcast")

                            Label {
                                anchors.centerIn: parent
                                text: "🎵"
                                font.pixelSize: 40
                            }
                        }

                        Rectangle {
                            anchors.bottom: parent.bottom
                            width: parent.width
                            height: 48
                            color: theme.mantle
                            visible: !playerContainer.isYoutube

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 8

                                Button {
                                    id: playPauseBtn
                                    flat: true
                                    font.pixelSize: 16
                                    text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                                    implicitWidth: 36
                                    implicitHeight: 36
                                    activeFocusOnTab: true
                                    onClicked: {
                                        if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                                            mediaPlayer.pause()
                                        else
                                            mediaPlayer.play()
                                    }
                                    Keys.onTabPressed:     { event.accepted = true; seekSlider.forceActiveFocus(Qt.TabFocusReason) }
                                    Keys.onRightPressed:   { event.accepted = true; seekSlider.forceActiveFocus(Qt.TabFocusReason) }
                                    Keys.onBacktabPressed: { event.accepted = true; itemList.forceActiveFocus(Qt.BacktabFocusReason) }
                                    Keys.onLeftPressed:    { event.accepted = true; itemList.forceActiveFocus(Qt.BacktabFocusReason) }
                                    background: Rectangle {
                                        radius: 6
                                        color: playPauseBtn.pressed ? theme.surface0 : playPauseBtn.hovered ? theme.surface1 : "transparent"
                                        border.color: playPauseBtn.activeFocus ? theme.amber : "transparent"
                                        border.width: playPauseBtn.activeFocus ? 2 : 0
                                    }
                                }

                                Slider {
                                    id: seekSlider
                                    Layout.fillWidth: true
                                    from: 0
                                    to: mediaPlayer.duration > 0 ? mediaPlayer.duration : 1
                                    value: mediaPlayer.position
                                    activeFocusOnTab: true
                                    onMoved: mediaPlayer.position = value
                                    Keys.onTabPressed:     { event.accepted = true; volumeSlider.forceActiveFocus(Qt.TabFocusReason) }
                                    Keys.onBacktabPressed: { event.accepted = true; playPauseBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                                    handle: Rectangle {
                                        x: seekSlider.leftPadding + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                                        y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                                        width: 14; height: 14; radius: 7
                                        color: seekSlider.pressed ? theme.amber : theme.surface1
                                        border.color: seekSlider.activeFocus ? theme.amber : theme.subtext
                                        border.width: seekSlider.activeFocus ? 2 : 1
                                    }
                                }

                                Label {
                                    text: _formatTime(mediaPlayer.position) + " / " + _formatTime(mediaPlayer.duration)
                                    color: theme.subtext
                                    font.pixelSize: 10
                                }

                                Label {
                                    text: "🔊"
                                    color: theme.subtext
                                    font.pixelSize: 12
                                }

                                Slider {
                                    id: volumeSlider
                                    Layout.preferredWidth: 80
                                    from: 0.0
                                    to: 1.0
                                    value: appSettings.volume
                                    activeFocusOnTab: true
                                    onMoved: { audioOutput.volume = value; appSettings.volume = value }
                                    Keys.onTabPressed:     { event.accepted = true; openBtnRect.forceActiveFocus(Qt.TabFocusReason) }
                                    Keys.onBacktabPressed: { event.accepted = true; seekSlider.forceActiveFocus(Qt.BacktabFocusReason) }
                                    handle: Rectangle {
                                        x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                                        y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                                        width: 14; height: 14; radius: 7
                                        color: volumeSlider.pressed ? theme.amber : theme.surface1
                                        border.color: volumeSlider.activeFocus ? theme.amber : theme.subtext
                                        border.width: volumeSlider.activeFocus ? 2 : 1
                                    }
                                }
                            }
                        }
                    }

                    // Text content block
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 20
                        Layout.leftMargin: 24
                        Layout.rightMargin: 24
                        Layout.bottomMargin: 24
                        spacing: 12

                        Label {
                            id: detailTitle
                            text: ""
                            color: theme.text
                            font.pixelSize: 22
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Rectangle {
                                height: 22
                                Layout.preferredWidth: typeLabel.implicitWidth + 14
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
                                Layout.fillWidth: true
                            }
                        }

                        // Divider
                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: theme.surface0
                        }

                        TextArea {
                            id: detailDescription
                            readOnly: true
                            wrapMode: Text.WordWrap
                            color: theme.text
                            background: null
                            textFormat: Text.RichText
                            font.pixelSize: 14
                            Layout.fillWidth: true
                            onLinkActivated: (link) => Qt.openUrlExternally(link)
                        }
                    }
                }
            }

            Rectangle {
                id: openBtnRect
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.leftMargin: 24
                anchors.bottomMargin: 12
                width: openBtn.implicitWidth + 32
                height: 36
                radius: 8
                activeFocusOnTab: true
                visible: detailTitle.text !== ""
                color: openBtn.pressed ? theme.blue + "cc"
                     : openBtn.containsMouse ? theme.blue
                     : theme.surface0
                border.color: (openBtn.containsMouse || openBtnRect.activeFocus) ? theme.amber : "transparent"
                border.width: 1

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
                Keys.onReturnPressed: Qt.openUrlExternally(detailUrl.text)
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Space) { Qt.openUrlExternally(detailUrl.text); event.accepted = true }
                }
                Keys.onTabPressed: {
                    event.accepted = true
                    if (firstHeaderBtn)
                        firstHeaderBtn.forceActiveFocus(Qt.TabFocusReason)
                }
                Keys.onRightPressed: {
                    event.accepted = true
                    if (firstHeaderBtn)
                        firstHeaderBtn.forceActiveFocus(Qt.TabFocusReason)
                }
                Keys.onBacktabPressed: {
                    event.accepted = true
                    if (playerContainer.visible && !playerContainer.isYoutube)
                        volumeSlider.forceActiveFocus(Qt.BacktabFocusReason)
                    else
                        itemList.forceActiveFocus(Qt.BacktabFocusReason)
                }
                Keys.onLeftPressed: {
                    event.accepted = true
                    if (playerContainer.visible && !playerContainer.isYoutube)
                        volumeSlider.forceActiveFocus(Qt.BacktabFocusReason)
                    else
                        itemList.forceActiveFocus(Qt.BacktabFocusReason)
                }
            }
        }
    }

    // Item delegate
    Component {
        id: itemDelegate

        Rectangle {
            width: itemList.width - itemVScroll.width
            height: 84
            color: itemList.currentIndex === index
                ? theme.surface0
                : itemMouse.containsMouse ? theme.surface0 + "80"
                : model.itemIsRead ? "transparent"
                : theme.mantle
            border.color: (itemMouse.containsMouse || ListView.isCurrentItem) ? theme.amber : "transparent"
            border.width: 1

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
                            Layout.preferredWidth: typeChip.implicitWidth + 10
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
                visible: !(itemMouse.containsMouse || itemList.currentIndex === index)
            }

            MouseArea {
                id: itemMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    itemList.currentIndex = index
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

    function _descHtml(raw) {
        if (!raw) return ""
        if (/<[a-zA-Z]/.test(raw)) return raw
        return raw
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br/>")
    }

    function _loadItem(item) {
        detailTitle.text = item.itemTitle
        detailMeta.text = item.itemPublished.substring(0, 16).replace("T", "  ")
        detailTypeStor.text = item.itemType
        detailDescription.text = _descHtml(item.itemDescription)
        detailUrl.text = item.itemUrl
        const isMedia = ["video", "audio", "short", "livestream"].includes(item.itemType)
        const embedUrl = _youtubeEmbedUrl(item.itemUrl)
        const isYt = embedUrl !== ""
        playerContainer.isYoutube = isYt
        if (isYt) {
            mediaPlayer.source = ""
            youtubeView.url = embedUrl
            playerContainer.visible = true
        } else if (isMedia && item.itemMediaUrl !== "") {
            youtubeView.url = "about:blank"
            mediaPlayer.source = item.itemMediaUrl
            playerContainer.visible = true
        } else {
            youtubeView.url = "about:blank"
            mediaPlayer.source = ""
            playerContainer.visible = false
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

    function _youtubeEmbedUrl(url) {
        if (!url) return ""
        var watchMatch = url.match(/youtube\.com\/watch\?.*v=([A-Za-z0-9_-]{11})/)
        if (watchMatch) return "https://www.youtube.com/embed/" + watchMatch[1]
        var shortMatch = url.match(/youtu\.be\/([A-Za-z0-9_-]{11})/)
        if (shortMatch) return "https://www.youtube.com/embed/" + shortMatch[1]
        return ""
    }
}
