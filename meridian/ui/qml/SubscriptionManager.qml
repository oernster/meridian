import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#1e1e2e"
    required property var controller
    signal close()

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 12

        RowLayout {
            Label {
                text: "Subscriptions"
                color: "#cdd6f4"
                font.pixelSize: 18
                font.bold: true
                Layout.fillWidth: true
            }
            Button {
                text: "Close"
                flat: true
                onClicked: root.close()
            }
        }

        // Add subscription form
        GroupBox {
            title: "Add Subscription"
            Layout.fillWidth: true

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                TextField {
                    id: urlField
                    placeholderText: "https://example.com/.well-known/mmsp.json"
                    Layout.fillWidth: true
                    color: "#cdd6f4"
                    background: Rectangle { color: "#313244"; radius: 4 }
                }

                ComboBox {
                    id: sourceTypeCombo
                    model: ["mfeed", "rss", "atom", "podcast", "platform"]
                    Layout.fillWidth: true
                }

                TextField {
                    id: platformIdField
                    placeholderText: "Platform ID (platform source type only)"
                    Layout.fillWidth: true
                    visible: sourceTypeCombo.currentText === "platform"
                    color: "#cdd6f4"
                    background: Rectangle { color: "#313244"; radius: 4 }
                }

                Button {
                    text: "Subscribe"
                    Layout.fillWidth: true
                    enabled: urlField.text.startsWith("https://")
                    onClicked: {
                        controller.subscribe(urlField.text.trim(), sourceTypeCombo.currentText)
                        urlField.text = ""
                        platformIdField.text = ""
                    }
                }
            }
        }

        // Subscription list
        ListView {
            id: subList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: controller.feedModel
            delegate: subDelegate
        }
    }

    Component {
        id: subDelegate
        Rectangle {
            width: subList.width
            height: 80
            color: index % 2 === 0 ? "#181825" : "#1e1e2e"
            radius: 4

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 4

                RowLayout {
                    Label {
                        text: model.feedTitle || model.feedUrl
                        color: "#cdd6f4"
                        font.pixelSize: 13
                        elide: Text.ElideRight
                        Layout.fillWidth: true
                    }

                    Button {
                        text: "Filter"
                        flat: true
                        font.pixelSize: 10
                        onClicked: {
                            filterDialog.feedId = model.feedId
                            filterDialog.feedTitle = model.feedTitle || model.feedUrl
                            filterDialog.open()
                        }
                    }

                    Button {
                        text: "Remove"
                        flat: true
                        font.pixelSize: 10
                        palette.button: "#f38ba8"
                        onClicked: {
                            confirmDialog.feedId = model.feedId
                            confirmDialog.feedTitle = model.feedTitle || model.feedUrl
                            confirmDialog.open()
                        }
                    }
                }

                Label {
                    text: model.feedUrl
                    color: "#6c7086"
                    font.pixelSize: 10
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }
    }

    Dialog {
        id: confirmDialog
        title: "Remove Subscription"
        property int feedId: 0
        property string feedTitle: ""
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent

        Label {
            text: "Remove \"" + confirmDialog.feedTitle + "\"? All items will be deleted."
            wrapMode: Text.WordWrap
            width: 300
            color: "#cdd6f4"
        }

        onAccepted: controller.unsubscribe(confirmDialog.feedId)
    }

    Dialog {
        id: filterDialog
        title: "Set Filter"
        property int feedId: 0
        property string feedTitle: ""
        standardButtons: Dialog.Ok | Dialog.Cancel
        anchors.centerIn: parent
        width: 400

        ColumnLayout {
            width: 360
            spacing: 8

            Label {
                text: "Filter for: " + filterDialog.feedTitle
                color: "#cdd6f4"
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            TextField {
                id: filterField
                placeholderText: "e.g. type:video AND duration:>=300"
                Layout.fillWidth: true
                color: "#cdd6f4"
                background: Rectangle { color: "#313244"; radius: 4 }
            }

            Label {
                text: "Leave empty to remove filter"
                color: "#6c7086"
                font.pixelSize: 10
            }
        }

        onAccepted: controller.setFilter(filterDialog.feedId, filterField.text)
        onOpened: filterField.text = ""
    }
}
