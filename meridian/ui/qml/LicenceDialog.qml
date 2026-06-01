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
            text: "Licence - GNU Lesser General Public Licence v3.0"
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
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Close"
            theme: root.theme
            onClicked: root.close()
        }
    }

    contentItem: ScrollView {
        clip: true
        contentWidth: availableWidth

        TextArea {
            readOnly: true
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            text: appLicenceText
            color: root.theme.text
            background: null
            font.family: "Courier New"
            font.pixelSize: 11
            leftPadding: 16
            rightPadding: 16
            topPadding: 12
            bottomPadding: 12
        }
    }
}
