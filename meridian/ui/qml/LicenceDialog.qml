import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    modal: true
    width: 510
    height: 560

    anchors.centerIn: Overlay.overlay

    required property var theme
    property string licenceTitle: ""
    property string licenceBody: ""

    onOpened: licenceText.forceActiveFocus(Qt.OtherFocusReason)

    background: Rectangle {
        color: theme.base
        border.color: theme.surface0
        border.width: 1
        radius: 8
    }

    header: Rectangle {
        width: parent.width
        height: 46
        color: theme.mantle
        radius: 8
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 8
            color: theme.mantle
        }
        Rectangle {
            anchors.bottom: parent.bottom
            width: parent.width
            height: 1
            color: theme.surface0
        }
        Label {
            anchors.centerIn: parent
            text: root.licenceTitle
            font.pixelSize: 14
            font.bold: true
            color: theme.text
        }
    }

    footer: Rectangle {
        width: parent.width
        height: 52
        color: theme.mantle
        radius: 8
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 8
            color: theme.mantle
        }
        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: theme.surface0
        }
        StyledButton {
            id: closeBtn
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Close"
            theme: root.theme
            onClicked: root.close()
            Keys.onReturnPressed: root.close()
            Keys.onEscapePressed: root.close()
            Keys.onBacktabPressed: {
                event.accepted = true
                licenceText.forceActiveFocus(Qt.BacktabFocusReason)
            }
        }
    }

    contentItem: ScrollView {
        clip: true
        contentWidth: availableWidth

        TextArea {
            id: licenceText
            readOnly: true
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            text: root.licenceBody
            color: root.theme.text
            background: null
            font.family: "Courier New"
            font.pixelSize: 11
            leftPadding: 16
            rightPadding: 16
            topPadding: 12
            bottomPadding: 12

            Keys.onTabPressed: {
                event.accepted = true
                closeBtn.forceActiveFocus(Qt.TabFocusReason)
            }
        }
    }
}
