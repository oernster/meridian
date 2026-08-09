import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import QtWebEngine

// The reader's media player: a video surface, a YouTube embed, or an audio
// placeholder, with the transport bar underneath.
//
// Extracted from FeedReader.qml. Which of the three it shows is its own
// business now: the caller says `show(mediaUrl, pageUrl)` and the panel works
// out whether the page is a YouTube watch link and plays the embed instead.
//
// The transport bar is not shown for a YouTube embed, because the embed brings
// its own. That is why the focus ring has to ask whether the panel is showing
// rather than assuming it is a stop.
Rectangle {
    id: panel

    required property var theme
    required property string mediaKind
    property real initialVolume: 0.2

    readonly property bool isYoutube: _isYoutube
    readonly property bool hasTransport: panel.visible && !panel._isYoutube

    signal volumeChosen(real value)
    signal focusForwardRequested()
    signal focusBackwardRequested()

    property bool _isYoutube: false

    readonly property int _transportHeight: 48

    visible: false
    color: "#000"
    radius: 0

    // Show whatever the item offers, and report whether anything is playable.
    function show(mediaUrl, pageUrl) {
        var embed = panel.embedUrlFor(pageUrl)
        panel._isYoutube = embed !== ""
        if (panel._isYoutube) {
            player.source = ""
            youtubeView.url = embed
            panel.visible = true
        } else if (mediaUrl !== "") {
            youtubeView.url = "about:blank"
            player.source = mediaUrl
            panel.visible = true
        } else {
            panel.hide()
        }
        return panel.visible
    }

    function hide() {
        youtubeView.url = "about:blank"
        player.source = ""
        panel.visible = false
    }

    function focusFirst() {
        playPauseBtn.forceActiveFocus(Qt.TabFocusReason)
    }

    function focusLast() {
        volumeSlider.forceActiveFocus(Qt.BacktabFocusReason)
    }

    function embedUrlFor(url) {
        if (!url) return ""
        var watch = url.match(/youtube\.com\/watch\?.*v=([A-Za-z0-9_-]{11})/)
        if (watch) return "https://www.youtube.com/embed/" + watch[1]
        var short = url.match(/youtu\.be\/([A-Za-z0-9_-]{11})/)
        if (short) return "https://www.youtube.com/embed/" + short[1]
        return ""
    }

    function formatTime(ms) {
        const s = Math.floor(ms / 1000)
        const h = Math.floor(s / 3600)
        const m = Math.floor((s % 3600) / 60)
        const sec = s % 60
        if (h > 0)
            return h + ":" + String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
        return String(m).padStart(2, "0") + ":" + String(sec).padStart(2, "0")
    }

    MediaPlayer {
        id: player
        videoOutput: videoOutput
        audioOutput: audioOutput
    }

    AudioOutput {
        id: audioOutput
        Component.onCompleted: volume = panel.initialVolume
    }

    VideoOutput {
        id: videoOutput
        anchors.fill: parent
        anchors.bottomMargin: panel._transportHeight
        visible: !panel._isYoutube
    }

    WebEngineView {
        id: youtubeView
        anchors.fill: parent
        anchors.bottomMargin: 0
        visible: panel._isYoutube
    }

    Rectangle {
        anchors.fill: parent
        anchors.bottomMargin: panel._transportHeight
        color: theme.mantle
        visible: !panel._isYoutube
                 && (panel.mediaKind === "audio" || panel.mediaKind === "podcast")

        Label {
            anchors.centerIn: parent
            text: "🎵"
            font.pixelSize: 40
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: panel._transportHeight
        color: theme.mantle
        visible: !panel._isYoutube

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 8

            Button {
                id: playPauseBtn
                objectName: "playPauseBtn"
                flat: true
                font.pixelSize: 16
                text: player.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                implicitWidth: 36
                implicitHeight: 36
                activeFocusOnTab: true
                onClicked: {
                    if (player.playbackState === MediaPlayer.PlayingState) player.pause()
                    else player.play()
                }
                Keys.onTabPressed:     { event.accepted = true; seekSlider.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onRightPressed:   { event.accepted = true; seekSlider.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; panel.focusBackwardRequested() }
                Keys.onLeftPressed:    { event.accepted = true; panel.focusBackwardRequested() }
                background: Rectangle {
                    radius: 6
                    color: playPauseBtn.pressed ? theme.surface0
                         : playPauseBtn.hovered ? theme.surface1
                         : "transparent"
                    border.color: playPauseBtn.activeFocus ? theme.amber : "transparent"
                    border.width: playPauseBtn.activeFocus ? 2 : 0
                }
            }

            Slider {
                id: seekSlider
                objectName: "seekSlider"
                Layout.fillWidth: true
                from: 0
                to: player.duration > 0 ? player.duration : 1
                value: player.position
                activeFocusOnTab: true
                onMoved: player.position = value
                Keys.onTabPressed:     { event.accepted = true; volumeSlider.forceActiveFocus(Qt.TabFocusReason) }
                Keys.onBacktabPressed: { event.accepted = true; playPauseBtn.forceActiveFocus(Qt.BacktabFocusReason) }
                handle: Rectangle {
                    x: seekSlider.leftPadding
                       + seekSlider.visualPosition * (seekSlider.availableWidth - width)
                    y: seekSlider.topPadding + seekSlider.availableHeight / 2 - height / 2
                    width: 14; height: 14; radius: 7
                    color: seekSlider.pressed ? theme.amber : theme.surface1
                    border.color: seekSlider.activeFocus ? theme.amber : theme.subtext
                    border.width: seekSlider.activeFocus ? 2 : 1
                }
            }

            Label {
                text: panel.formatTime(player.position) + " / " + panel.formatTime(player.duration)
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
                objectName: "volumeSlider"
                Layout.preferredWidth: 80
                from: 0.0
                to: 1.0
                value: panel.initialVolume
                activeFocusOnTab: true
                onMoved: {
                    audioOutput.volume = value
                    panel.volumeChosen(value)
                }
                Keys.onTabPressed:     { event.accepted = true; panel.focusForwardRequested() }
                Keys.onBacktabPressed: { event.accepted = true; seekSlider.forceActiveFocus(Qt.BacktabFocusReason) }
                handle: Rectangle {
                    x: volumeSlider.leftPadding
                       + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
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
