import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// A modal dialog with a Cancel and an OK, taking arbitrary content.
//
// Extracted from SubscriptionManager.qml, where the edit-URL and filter
// dialogs wrote out the same background, the same mantle-and-hairline footer,
// the same button pair with the same Left and Right wiring between them, plus
// the same padding. What differs between the two is entirely their content, so
// that is all a caller declares.
//
// `ConfirmDialog` is the message-only sibling of this. The two are kept apart
// because a message dialog sizes to its text while a form sizes to its fields.
Dialog {
    id: control

    required property var theme

    default property alias content: contentColumn.data

    modal: true
    anchors.centerIn: Overlay.overlay

    topPadding: 16
    leftPadding: 16
    rightPadding: 16
    bottomPadding: 16

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
                id: cancelBtn
                objectName: "cancelBtn"
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
                Keys.onLeftPressed: { cancelBtn.forceActiveFocus(); event.accepted = true }
            }
        }
    }

    contentItem: ColumnLayout {
        id: contentColumn
        spacing: 12
    }
}
