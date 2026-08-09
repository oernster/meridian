import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// One discovery search result: checkbox, favicon, title with source badge,
// description, URL and a subscribe action.
//
// Extracted from FeedDiscovery.qml, where it was an inline `Component` reading
// the enclosing file for everything it needed: `model.*` for its content,
// `root.selectedUrls` for its selected state, `root._toggleUrl` and
// `controller.subscribeFromDiscovery` for its actions. That works only while
// it sits inside that one file. Every input is now a declared property and
// every action is a signal, so the row can be instantiated and tested on its
// own.
//
// The six `candidate*` properties are `required`, which is what makes the view
// bind them from the model roles of the same name. They stay properties of the
// root rather than locals because the ListView's own Space and Return handlers
// read them back off `currentItem`.
Rectangle {
    id: row

    // Bound by the view from FeedCandidateModel's roles.
    required property string candidateUrl
    required property string candidateTitle
    required property string candidateDescription
    required property string candidateFaviconUrl
    required property string candidateSourceType
    required property bool candidateIsSubscribed

    // Set by the caller.
    required property var theme
    required property bool selected

    signal toggleRequested()
    signal subscribeRequested()

    height: 78
    clip: true
    color: (row.selected || rowHover.hovered || row.ListView.isCurrentItem)
           ? theme.mantle : theme.base
    border.color: (rowHover.hovered || row.ListView.isCurrentItem) ? theme.amber : "transparent"
    border.width: 1
    opacity: row.candidateIsSubscribed ? 0.55 : 1.0

    // Double-click instant subscribe (single item)
    TapHandler {
        enabled: !row.candidateIsSubscribed
        onDoubleTapped: row.subscribeRequested()
    }

    RowLayout {
        x: 8
        y: 8
        width: parent.width - 18
        height: parent.height - 16
        spacing: 8
        z: 1

        // Checkbox (locked when subscribed)
        Rectangle {
            Layout.preferredWidth: 18
            Layout.preferredHeight: 18
            Layout.minimumWidth: 18
            Layout.minimumHeight: 18
            Layout.maximumWidth: 18
            Layout.maximumHeight: 18
            radius: 3
            color: (row.selected && !row.candidateIsSubscribed) ? theme.blue : "transparent"
            border.color: row.candidateIsSubscribed ? theme.overlay : theme.blue
            border.width: 2
            Label {
                anchors.centerIn: parent
                text: (row.candidateIsSubscribed || row.selected) ? "✓" : ""
                color: row.candidateIsSubscribed ? theme.overlay
                     : theme.isDark ? "#1e1e2e" : "#ffffff"
                font.pixelSize: 11
                font.bold: true
            }
            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: row.candidateIsSubscribed ? Qt.ArrowCursor : Qt.PointingHandCursor
                enabled: !row.candidateIsSubscribed
                onClicked: row.toggleRequested()
            }
        }

        // Favicon or fallback initial: fixed-size Item isolates image implicitSize from RowLayout
        Item {
            Layout.preferredWidth: 32
            Layout.preferredHeight: 32
            Layout.minimumWidth: 32
            Layout.minimumHeight: 32
            Layout.maximumWidth: 32
            Layout.maximumHeight: 32

            Rectangle {
                width: 32; height: 32; radius: 6
                color: theme.surface0
                visible: row.candidateFaviconUrl === ""
                Label {
                    anchors.centerIn: parent
                    text: (row.candidateTitle || row.candidateUrl).charAt(0).toUpperCase()
                    color: theme.blue
                    font.pixelSize: 14
                    font.bold: true
                }
            }
            Image {
                width: 32; height: 32
                source: row.candidateFaviconUrl
                sourceSize: Qt.size(32, 32)
                fillMode: Image.PreserveAspectFit
                visible: row.candidateFaviconUrl !== ""
            }
        }

        // Text content
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                Label {
                    objectName: "titleLabel"
                    text: row.candidateTitle || row.candidateUrl
                    color: theme.text
                    font.pixelSize: 13
                    font.bold: true
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    wrapMode: Text.NoWrap
                    Layout.fillWidth: true
                }

                Rectangle {
                    height: 18
                    width: badgeLbl.contentWidth + 10
                    radius: 3
                    color: theme.surface0

                    Label {
                        id: badgeLbl
                        objectName: "badgeLabel"
                        anchors.centerIn: parent
                        text: (row.candidateSourceType || "RSS").toUpperCase()
                        color: theme.blue
                        font.pixelSize: 9
                        font.bold: true
                    }
                }
            }

            Label {
                text: row.candidateDescription
                color: theme.subtext
                font.pixelSize: 11
                elide: Text.ElideRight
                maximumLineCount: 1
                wrapMode: Text.NoWrap
                Layout.fillWidth: true
                visible: row.candidateDescription !== ""
            }

            Label {
                text: row.candidateUrl
                color: theme.overlay
                font.pixelSize: 10
                elide: Text.ElideRight
                Layout.fillWidth: true
            }
        }

        // Subscribe / Subscribed indicator
        Rectangle {
            implicitHeight: 28
            implicitWidth: rowActionLbl.implicitWidth + 16
            radius: 5
            color: {
                if (row.candidateIsSubscribed) return "transparent"
                return rowActionMouse.containsMouse ? theme.surface0 : "transparent"
            }
            border.color: row.candidateIsSubscribed ? theme.overlay : theme.green
            border.width: 1

            Label {
                id: rowActionLbl
                objectName: "rowActionLabel"
                anchors.centerIn: parent
                text: row.candidateIsSubscribed ? "Subscribed" : "Subscribe"
                color: row.candidateIsSubscribed ? theme.overlay : theme.green
                font.pixelSize: 11
                font.bold: true
            }

            MouseArea {
                id: rowActionMouse
                objectName: "rowActionMouse"
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: row.candidateIsSubscribed ? Qt.ArrowCursor : Qt.PointingHandCursor
                enabled: !row.candidateIsSubscribed
                onClicked: row.subscribeRequested()
            }
        }
    }

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: theme.surface0
        opacity: 0.5
        visible: !rowHover.hovered && !row.ListView.isCurrentItem && !row.selected
    }

    HoverHandler { id: rowHover }
}
