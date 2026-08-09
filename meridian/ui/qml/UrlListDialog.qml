import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A modal dialog showing a heading over a scrollable list of feed URLs.
//
// Extracted from FeedDiscovery.qml, where the bulk-confirm and bulk-result
// dialogs carried the same chrome twice: identical size, padding and
// background, plus a footer built from a mantle strip, a hairline rule and a
// right-aligned button row. The two differed only in their heading, the list
// they showed and their buttons, which is exactly what this exposes.
//
// Buttons are declared as default children by the caller and reparented into
// the footer row. They keep the caller's scope, so `root.theme` and the
// dialog's own id resolve there as they did when they were written inline.
Dialog {
    id: control

    property alias heading: headingLabel.text
    property var urls: []

    default property alias buttons: buttonRow.data

    modal: true
    anchors.centerIn: Overlay.overlay
    width: 460
    height: 360
    topPadding: 16; leftPadding: 16; rightPadding: 16; bottomPadding: 8

    background: Rectangle {
        color: theme.base
        border.color: theme.surface0
        radius: 8
    }

    footer: Rectangle {
        color: theme.mantle
        height: 52
        radius: 8
        Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
        Row {
            id: buttonRow
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8
        }
    }

    contentItem: ColumnLayout {
        spacing: 12

        Label {
            id: headingLabel
            // Named so tests/ui/test_url_list_dialog.py can assert the
            // heading and the list actually reach these, rather than only
            // that the properties round-trip on the dialog.
            objectName: "headingLabel"
            color: theme.text
            font.bold: true
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }

        ListView {
            id: urlList
            objectName: "urlList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: control.urls
            ScrollBar.vertical: ScrollBar { id: urlScrollBar; policy: ScrollBar.AlwaysOn }

            // A list short enough to fit is left alone; a bulk subscribe of
            // thirty URLs reads itself so the reader can check what they are
            // about to confirm without reaching for the wheel.
            AutoScroller {
                objectName: "urlListScroller"
                flick: urlList
                scrollBar: urlScrollBar
                active: control.visible
            }
            delegate: Label {
                text: "• " + modelData
                color: theme.subtext
                font.pixelSize: 11
                elide: Text.ElideRight
                width: urlList.width - 16
                height: 22
            }
        }
    }
}
