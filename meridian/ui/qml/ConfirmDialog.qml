import QtQuick
import QtQuick.Controls

// A modal message with a Cancel and an OK; or with OK alone.
//
// Extracted from main.qml, which carried this chrome three times: the single
// feed removal, the bulk removal and the error report. All three had the same
// background, the same mantle-and-hairline footer and the same right-aligned
// button row; they differed only in their title, their message and what OK
// meant. The caller supplies those and handles `accepted`.
//
// Removal is destructive, so the confirmation is not optional: both removal
// paths name what is going and what goes with it.
Dialog {
    id: control

    required property var theme
    property string message: ""

    // The error report has nothing to cancel, so it shows OK alone.
    property bool okOnly: false

    // The removal messages are two lines and read better opened up; the error
    // report is a single line and does not want the extra leading.
    property real bodyLineHeight: 1.4

    readonly property int _bodyWidth: 320

    modal: true
    anchors.centerIn: Overlay.overlay

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
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            spacing: 8

            StyledButton {
                id: cancelBtn
                objectName: "cancelBtn"
                visible: !control.okOnly
                text: "Cancel"
                theme: control.theme
                onClicked: control.reject()
                Keys.onReturnPressed: { control.reject(); event.accepted = true }
                Keys.onRightPressed: { okBtn.forceActiveFocus(); event.accepted = true }
            }
            StyledButton {
                id: okBtn
                objectName: "okBtn"
                text: "OK"
                theme: control.theme
                onClicked: control.accept()
                Keys.onReturnPressed: { control.accept(); event.accepted = true }
                Keys.onLeftPressed: {
                    if (cancelBtn.visible) cancelBtn.forceActiveFocus()
                    event.accepted = true
                }
            }
        }
    }

    Label {
        objectName: "messageLabel"
        text: control.message
        color: theme.text
        wrapMode: Text.WordWrap
        width: control._bodyWidth
        lineHeight: control.bodyLineHeight
    }
}
