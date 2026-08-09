import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Re-point a subscription at a different URL.
//
// Extracted from SubscriptionManager.qml. It carries the feed it was opened on
// so the caller can read it back; it reports through `urlAccepted` rather
// than calling the controller itself.
FormDialog {
    id: dialog

    property int feedId: 0
    property string currentUrl: ""

    signal urlAccepted(int feedId, string url)

    title: "Edit Feed URL"
    width: 460

    Label {
        text: "Feed URL"
        color: dialog.theme.text
        font.bold: true
        Layout.fillWidth: true
    }

    TextField {
        id: urlField
        objectName: "editUrlField"
        Layout.fillWidth: true
        color: dialog.theme.text
        placeholderTextColor: dialog.theme.overlay
        font.pixelSize: 13
        background: Rectangle {
            color: dialog.theme.surface1
            border.color: urlField.activeFocus ? dialog.theme.blue : dialog.theme.overlay
            border.width: urlField.activeFocus ? 2 : 1
            radius: 6
        }
        leftPadding: 10
        rightPadding: 10
        topPadding: 8
        bottomPadding: 8
        Keys.onReturnPressed: {
            if (text.trim()) {
                dialog.accept()
                event.accepted = true
            }
        }
    }

    onOpened: {
        urlField.text = dialog.currentUrl
        urlField.forceActiveFocus()
    }
    onAccepted: dialog.urlAccepted(dialog.feedId, urlField.text.trim())
}
