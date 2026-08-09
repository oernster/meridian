import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// The URL field and the Subscribe button at the top of the manager.
//
// Extracted from SubscriptionManager.qml. The `https://` test appeared six
// times across the button's enabled state, its colour, its opacity, its cursor
// and both key handlers; it is one readonly property here.
//
// Subscribe is only a tab stop while the field holds an acceptable URL, so
// both ends of the ring have to ask rather than assume, which is what
// focusLast is for.
Rectangle {
    id: bar

    required property var theme

    readonly property alias url: urlField.text
    readonly property bool canSubscribe: urlField.text.trim().startsWith("https://")

    signal subscribeRequested(string url)
    signal focusForwardRequested()

    function focusFirst() {
        urlField.forceActiveFocus()
    }

    function focusLast() {
        if (bar.canSubscribe) subscribeButton.forceActiveFocus()
        else urlField.forceActiveFocus()
    }

    function _submit() {
        if (!bar.canSubscribe) return
        bar.subscribeRequested(urlField.text.trim())
        urlField.text = ""
    }

    implicitHeight: addColumn.implicitHeight + 32
    color: theme.mantle

    ColumnLayout {
        id: addColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 10

        Label {
            text: "Add Subscription"
            font.pixelSize: 13
            font.bold: true
            color: theme.subtext
            font.letterSpacing: 0.6
        }

        TextField {
            id: urlField
            objectName: "urlField"
            placeholderText: "https://example.com/.well-known/mmsp.json"
            Layout.fillWidth: true
            color: theme.text
            placeholderTextColor: theme.overlay
            font.pixelSize: 13
            background: Rectangle {
                color: theme.base
                border.color: urlField.activeFocus ? theme.blue : theme.surface1
                border.width: urlField.activeFocus ? 2 : 1
                radius: 6
            }
            leftPadding: 10
            rightPadding: 10
            topPadding: 8
            bottomPadding: 8
            Keys.onRightPressed: { bar.focusForwardRequested(); event.accepted = true }
        }

        Rectangle {
            id: subscribeButton
            objectName: "subscribeButton"
            Layout.fillWidth: true
            height: 38
            radius: 8
            activeFocusOnTab: bar.canSubscribe
            color: subscribeMouse.pressed ? theme.blue + "cc"
                 : bar.canSubscribe ? (subscribeMouse.containsMouse ? theme.blue + "dd" : theme.blue)
                 : theme.surface1
            opacity: bar.canSubscribe ? 1.0 : 0.5
            border.color: (activeFocus || (subscribeMouse.containsMouse && bar.canSubscribe))
                          ? theme.amber : "transparent"
            border.width: 1

            Keys.onReturnPressed: {
                if (bar.canSubscribe) {
                    bar._submit()
                    event.accepted = true
                }
            }
            Keys.onSpacePressed: {
                if (bar.canSubscribe) {
                    bar._submit()
                    event.accepted = true
                }
            }

            Label {
                anchors.centerIn: parent
                text: "Subscribe"
                color: theme.isDark ? "#1e1e2e" : "#ffffff"
                font.pixelSize: 13
                font.bold: true
            }

            MouseArea {
                id: subscribeMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: bar.canSubscribe ? Qt.PointingHandCursor : Qt.ArrowCursor
                property bool pressed: false
                property bool containsMouse: false
                enabled: bar.canSubscribe
                onEntered: containsMouse = true
                onExited: containsMouse = false
                onPressed: pressed = true
                onReleased: pressed = false
                onClicked: bar._submit()
            }
        }

        Item { height: 4 }
    }
}
