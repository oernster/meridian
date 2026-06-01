import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root
    modal: true
    width: 460
    height: 520
    standardButtons: Dialog.Close
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
            text: "About Meridian"
            font.pixelSize: 15
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
        Button {
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Close"
            onClicked: root.close()
        }
    }

    contentItem: Item {
        implicitWidth: 460

        ColumnLayout {
            id: contentCol
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            // Icon + identity
            RowLayout {
                Layout.fillWidth: true
                spacing: 18

                Image {
                    source: appIconUrl
                    sourceSize.width: 80
                    sourceSize.height: 80
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    Layout.maximumWidth: 80
                    Layout.maximumHeight: 80
                    fillMode: Image.PreserveAspectFit
                    visible: appIconUrl !== ""
                }

                Rectangle {
                    Layout.preferredWidth: 80
                    Layout.preferredHeight: 80
                    radius: 14
                    color: theme.surface0
                    visible: appIconUrl === ""
                    Label {
                        anchors.centerIn: parent
                        text: "M"
                        font.pixelSize: 36
                        font.bold: true
                        color: theme.blue
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5
                    Label {
                        text: "Meridian"
                        font.pixelSize: 26
                        font.bold: true
                        color: theme.text
                    }
                    Label {
                        text: "Version " + appVersion
                        color: theme.blue
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Label {
                        text: "MMSP Feed Reader"
                        color: theme.subtext
                        font.pixelSize: 12
                    }
                    Label {
                        text: "© Oliver Ernster"
                        color: theme.subtext
                        font.pixelSize: 12
                    }
                }
            }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.surface0 }

            Label {
                text: "Open Source Components"
                font.pixelSize: 13
                font.bold: true
                color: theme.text
            }

            GridLayout {
                Layout.fillWidth: true
                columns: 2
                columnSpacing: 20
                rowSpacing: 4

                Label { text: "PySide6 (Qt for Python)"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "LGPLv3"; color: theme.overlay; font.pixelSize: 11 }

                Label { text: "SQLAlchemy"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "MIT"; color: theme.overlay; font.pixelSize: 11 }

                Label { text: "httpx"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "BSD 3-Clause"; color: theme.overlay; font.pixelSize: 11 }

                Label { text: "defusedxml"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "PSFLv2"; color: theme.overlay; font.pixelSize: 11 }

                Label { text: "python-dateutil"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "Apache 2.0"; color: theme.overlay; font.pixelSize: 11 }

                Label { text: "bleach"; color: theme.subtext; font.pixelSize: 12 }
                Label { text: "Apache 2.0"; color: theme.overlay; font.pixelSize: 11 }
            }

            Item { Layout.fillHeight: true }

            Rectangle { Layout.fillWidth: true; height: 1; color: theme.surface0 }

            Label {
                text: "Licensed under the Apache License, Version 2.0"
                color: theme.overlay
                font.pixelSize: 11
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                bottomPadding: 4
            }
        }
    }
}
