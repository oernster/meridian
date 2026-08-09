import QtQuick
import QtQuick.Controls

// The update prompt: Download / Skip This Version / Later.
//
// The same chrome as ConfirmDialog, but three outcomes instead of two: Later
// simply closes (the next automatic check will offer again), Skip persists the
// offered tag so that version never prompts again and Download opens the
// platform asset, falling back to the release page when no asset matched.
Dialog {
    id: control

    required property var theme

    property string latestVersion: ""
    property string currentVersion: ""
    property string downloadUrl: ""
    property string pageUrl: ""

    signal downloadRequested()
    signal skipRequested()

    // The message wraps to this; wide enough that the two lines read whole.
    property int bodyWidth: 340

    title: "Update Available"
    modal: true
    anchors.centerIn: Overlay.overlay

    onOpened: downloadBtn.forceActiveFocus(Qt.OtherFocusReason)

    background: Rectangle {
        color: theme.base
        border.color: theme.surface0
        radius: 8
    }

    footer: Rectangle {
        color: theme.mantle
        implicitHeight: 52
        height: 52
        radius: 8
        Rectangle { anchors.top: parent.top; width: parent.width; height: 8; color: theme.mantle }
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: theme.surface0 }
        Row {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            StyledButton {
                id: downloadBtn
                objectName: "downloadBtn"
                text: "Download"
                theme: control.theme
                onClicked: { control.downloadRequested(); control.close() }
                Keys.onReturnPressed: { control.downloadRequested(); control.close(); event.accepted = true }
                Keys.onRightPressed: { skipBtn.forceActiveFocus(); event.accepted = true }
            }
            StyledButton {
                id: skipBtn
                objectName: "skipBtn"
                text: "Skip This Version"
                theme: control.theme
                onClicked: { control.skipRequested(); control.close() }
                Keys.onReturnPressed: { control.skipRequested(); control.close(); event.accepted = true }
                Keys.onLeftPressed: { downloadBtn.forceActiveFocus(); event.accepted = true }
                Keys.onRightPressed: { laterBtn.forceActiveFocus(); event.accepted = true }
            }
            StyledButton {
                id: laterBtn
                objectName: "laterBtn"
                text: "Later"
                theme: control.theme
                onClicked: control.close()
                Keys.onReturnPressed: { control.close(); event.accepted = true }
                Keys.onLeftPressed: { skipBtn.forceActiveFocus(); event.accepted = true }
            }
        }
    }

    Label {
        objectName: "updateMessageLabel"
        text: "Meridian " + control.latestVersion + " is available.\n"
            + "You are running " + control.currentVersion + "."
        color: theme.text
        wrapMode: Text.WordWrap
        width: control.bodyWidth
        lineHeight: 1.4
    }
}
