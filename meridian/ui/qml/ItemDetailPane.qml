import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The right-hand pane: the placeholder, the article itself, and the button
// that opens it in a browser.
//
// Extracted from FeedReader.qml, where the pane's state lived in three hidden
// `Label`s parked outside the layout so it would survive a rebuild. They are
// ordinary properties now, which is what a component can have and an inline
// block could not.
//
// The media panel is the awkward part of the focus ring: it is only a stop
// while something is playing that is not a YouTube embed, so both neighbours
// have to ask.
Rectangle {
    id: pane

    required property var theme
    property real initialVolume: 0.2

    property string itemTitle: ""
    property string itemMeta: ""
    property string itemType: ""
    property string itemDescription: ""
    property string itemUrl: ""
    property string itemThumbnail: ""

    // FeedReader hands this out to the window as its own lastFocusItem.
    readonly property alias lastFocusItem: openButton

    signal volumeChosen(real value)
    signal focusForwardRequested()
    signal focusBackwardRequested()

    readonly property bool _hasItem: pane.itemTitle !== ""
    readonly property var _mediaTypes: ["video", "audio", "short", "livestream"]

    color: theme.base

    function load(item) {
        pane.itemTitle = item.itemTitle
        pane.itemMeta = item.itemPublished.substring(0, 16).replace("T", "  ")
        pane.itemType = item.itemType
        pane.itemDescription = pane._descriptionHtml(item.itemDescription)
        pane.itemUrl = item.itemUrl
        pane.itemThumbnail = item.itemThumbnail || ""

        var playable = pane._mediaTypes.indexOf(item.itemType) >= 0
                       && item.itemMediaUrl !== ""
        mediaPanel.show(playable ? item.itemMediaUrl : "", item.itemUrl)
    }

    function clear() {
        pane.itemTitle = ""
        pane.itemMeta = ""
        pane.itemType = ""
        pane.itemDescription = ""
        pane.itemUrl = ""
        pane.itemThumbnail = ""
        mediaPanel.hide()
    }

    // The transport bar is the first stop when it is showing at all.
    function focusFirst() {
        if (mediaPanel.hasTransport) mediaPanel.focusFirst()
        else openButton.forceActiveFocus(Qt.TabFocusReason)
    }

    function _backFromOpenButton() {
        if (mediaPanel.hasTransport) mediaPanel.focusLast()
        else pane.focusBackwardRequested()
    }

    // Plain text arrives without markup and has to be escaped; anything that
    // already looks like HTML is passed through as the feed wrote it.
    function _descriptionHtml(raw) {
        if (!raw) return ""
        if (/<[a-zA-Z]/.test(raw)) return raw
        return raw
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\n/g, "<br/>")
    }

    // Empty state
    ColumnLayout {
        objectName: "emptyState"
        anchors.centerIn: parent
        spacing: 12
        visible: !pane._hasItem

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

    ScrollView {
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: openButton.top
        anchors.bottomMargin: 8
        clip: true
        contentWidth: availableWidth
        visible: pane._hasItem

        ColumnLayout {
            width: parent.width
            spacing: 0

            // Hero thumbnail: full width, fixed height, crop-fill
            Image {
                visible: pane.itemThumbnail !== "" && !mediaPanel.visible
                source: pane.itemThumbnail
                Layout.fillWidth: true
                Layout.preferredHeight: implicitHeight
                Layout.maximumHeight: 360
                fillMode: Image.PreserveAspectFit
                clip: false
            }

            MediaPlayerPanel {
                id: mediaPanel
                objectName: "mediaPanel"
                theme: pane.theme
                mediaKind: pane.itemType
                initialVolume: pane.initialVolume
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(pane.height * 0.38, 340)
                onVolumeChosen: function(value) { pane.volumeChosen(value) }
                onFocusForwardRequested: openButton.forceActiveFocus(Qt.TabFocusReason)
                onFocusBackwardRequested: pane.focusBackwardRequested()
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
                    objectName: "detailTitle"
                    text: pane.itemTitle
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
                            text: pane.itemType.toUpperCase()
                            color: theme.blue
                            font.pixelSize: 10
                            font.bold: true
                            font.letterSpacing: 0.8
                        }
                    }

                    Label {
                        objectName: "detailMeta"
                        text: pane.itemMeta
                        color: theme.subtext
                        font.pixelSize: 12
                        Layout.fillWidth: true
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: theme.surface0
                }

                TextArea {
                    objectName: "detailDescription"
                    text: pane.itemDescription
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
        id: openButton
        objectName: "openButton"
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.leftMargin: 24
        anchors.bottomMargin: 12
        width: openLabel.implicitWidth + 32
        height: 36
        radius: 8
        activeFocusOnTab: true
        visible: pane._hasItem
        color: openMouse.pressed ? theme.blue + "cc"
             : openMouse.containsMouse ? theme.blue
             : theme.surface0
        border.color: (openMouse.containsMouse || openButton.activeFocus)
                      ? theme.amber : "transparent"
        border.width: 1

        Label {
            id: openLabel
            anchors.centerIn: parent
            text: "Open in Browser →"
            color: openMouse.containsMouse ? (theme.isDark ? "#1e1e2e" : "#ffffff")
                 : theme.text
            font.pixelSize: 13
        }

        MouseArea {
            id: openMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: Qt.openUrlExternally(pane.itemUrl)
        }

        Keys.onReturnPressed: Qt.openUrlExternally(pane.itemUrl)
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Space) {
                Qt.openUrlExternally(pane.itemUrl)
                event.accepted = true
            }
        }
        Keys.onTabPressed:     { event.accepted = true; pane.focusForwardRequested() }
        Keys.onRightPressed:   { event.accepted = true; pane.focusForwardRequested() }
        Keys.onBacktabPressed: { event.accepted = true; pane._backFromOpenButton() }
        Keys.onLeftPressed:    { event.accepted = true; pane._backFromOpenButton() }
    }
}
