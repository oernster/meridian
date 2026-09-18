import QtQuick
import QtQuick.Controls

// A dialog of words to read: a title, a page that reads itself and Close.
//
// The one home for the licence dialogs and the Guide. They were two copies of
// the same chrome, the same self-reading page and the same focus rules, which
// is how the licence came to open on its text while the Guide opened on Close.
//
// The page is words, not a control. So the dialog opens on Close; the page is
// a stop only while it overflows, is reached by Tab alone (a click never takes
// focus from the reader) and paints no ring in any state. Tab, Right, Shift+Tab
// and Left all step between Close and the page, so the two form one ring.
//
// `namePrefix` names the parts ("licence" gives licenceScroll, licenceScroller,
// licenceText and licenceCloseBtn) so tests and callers find each by name.
Dialog {
    id: root
    modal: true

    anchors.centerIn: Overlay.overlay

    required property var theme
    required property string namePrefix
    property string heading: ""
    property string body: ""
    property int bodyFormat: TextEdit.PlainText
    property string bodyFontFamily: ""
    property int bodyFontSize: 13
    property color bodyColor: theme.text
    property int bodyPadding: 16

    onOpened: closeBtn.forceActiveFocus(Qt.TabFocusReason)

    function _toPage(reason) {
        if (pageText.activeFocusOnTab)
            pageText.forceActiveFocus(reason)
    }

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
            text: root.heading
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
            objectName: root.namePrefix + "CloseBtn"
            anchors.right: parent.right
            anchors.rightMargin: 12
            anchors.verticalCenter: parent.verticalCenter
            text: "Close"
            theme: root.theme
            onClicked: root.close()
            Keys.onReturnPressed: root.close()
            Keys.onEscapePressed: root.close()
            // The page is the only other stop, only while it overflows; with
            // nothing to scroll, focus stays here.
            Keys.onTabPressed:     { event.accepted = true; root._toPage(Qt.TabFocusReason) }
            Keys.onRightPressed:   { event.accepted = true; root._toPage(Qt.TabFocusReason) }
            Keys.onBacktabPressed: { event.accepted = true; root._toPage(Qt.BacktabFocusReason) }
            Keys.onLeftPressed:    { event.accepted = true; root._toPage(Qt.BacktabFocusReason) }
        }
    }

    // Reads only while the dialog is open; freezes in place rather than
    // restarting when it closes.
    AutoScroller {
        objectName: root.namePrefix + "Scroller"
        flick: pageScroll.contentItem
        scrollBar: pageScroll.ScrollBar.vertical
        active: root.visible
    }

    contentItem: ScrollView {
        id: pageScroll
        objectName: root.namePrefix + "Scroll"
        clip: true
        contentWidth: availableWidth

        TextArea {
            id: pageText
            objectName: root.namePrefix + "Text"
            readOnly: true
            textFormat: root.bodyFormat
            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
            text: root.body
            color: root.bodyColor
            // No ring in any state: this is words to read, not a control.
            background: null
            font.family: root.bodyFontFamily !== "" ? root.bodyFontFamily
                                                    : Qt.application.font.family
            font.pixelSize: root.bodyFontSize
            leftPadding: root.bodyPadding
            rightPadding: root.bodyPadding
            topPadding: 12
            bottomPadding: 12

            activeFocusOnTab: pageScroll.contentHeight > pageScroll.height
            activeFocusOnPress: false

            Keys.onTabPressed:     { event.accepted = true; closeBtn.forceActiveFocus(Qt.TabFocusReason) }
            Keys.onRightPressed:   { event.accepted = true; closeBtn.forceActiveFocus(Qt.TabFocusReason) }
            Keys.onBacktabPressed: { event.accepted = true; closeBtn.forceActiveFocus(Qt.BacktabFocusReason) }
            Keys.onLeftPressed:    { event.accepted = true; closeBtn.forceActiveFocus(Qt.BacktabFocusReason) }
        }
    }
}
