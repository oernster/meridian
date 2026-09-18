import QtQuick
import QtQuick.Controls

// The Help button's menu: the Guide, then About.
//
// Meridian has no menu bar, so Help is a button on the header that drops this
// open, the way Audio Deck's Help button does. It is a dropdown on the ring:
// Enter, Space or Down on the button open it with the first entry already
// focused; Up and Down walk the entries and wrap; Enter or Space chooses;
// Escape closes it back onto the button; Tab and Right leave it forward,
// Shift+Tab and Left leave it backward, so the ring is never trapped here.
//
// Choosing an entry reports it rather than acting: which dialog opens is the
// window's business. Focus is handed back to the button first, so the dialog
// that opens next returns focus there when it closes.
Popup {
    id: menu

    required property var theme

    // The button that opened the menu. Escape and a choice hand focus back to
    // it; the menu hangs beneath it.
    property Item opener: null

    signal guideRequested()
    signal aboutRequested()

    // Tab or Right off the menu; Shift+Tab or Left off it.
    signal focusForwardRequested()
    signal focusBackwardRequested()

    readonly property var _entries: [
        { key: "guide", label: "Guide" },
        { key: "about", label: "About Meridian" }
    ]
    readonly property int _entryHeight: 36
    readonly property int _padding: 4
    readonly property int _gap: 6

    parent: Overlay.overlay
    padding: _padding
    width: 200
    height: _entries.length * _entryHeight + _padding * 2
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

    // Opens beneath `item`, held inside the window: the Help button sits at
    // the right-hand end of the header, so a menu aligned to its left edge
    // would hang off the window.
    function openUnder(item) {
        menu.opener = item
        var below = item.mapToItem(Overlay.overlay, 0, item.height + menu._gap)
        menu.x = Math.max(0, Math.min(below.x, Overlay.overlay.width - menu.width))
        menu.y = below.y
        menu.open()
    }

    function _entry(index) {
        return entryRepeater.itemAt(index)
    }

    function _step(from, delta) {
        var count = entryRepeater.count
        menu._entry((from + delta + count) % count).forceActiveFocus(Qt.TabFocusReason)
    }

    function _choose(key) {
        menu.close()
        if (menu.opener)
            menu.opener.forceActiveFocus(Qt.OtherFocusReason)
        if (key === "guide")
            menu.guideRequested()
        else
            menu.aboutRequested()
    }

    function _leave(forward) {
        menu.close()
        if (forward)
            menu.focusForwardRequested()
        else
            menu.focusBackwardRequested()
    }

    // A menu that was asked for opens with something offered, so the first
    // entry is focused as it opens, with no extra keypress.
    onOpened: menu._entry(0).forceActiveFocus(Qt.TabFocusReason)

    background: Rectangle {
        color: theme.mantle
        border.color: theme.surface0
        border.width: 1
        radius: 6
    }

    Column {
        anchors.fill: parent
        spacing: 0

        Repeater {
            id: entryRepeater

            Rectangle {
                id: entry
                objectName: "helpMenu_" + modelData.key

                required property var modelData
                required property int index

                width: parent.width
                height: menu._entryHeight
                radius: 4
                color: (entryMouse.containsMouse || activeFocus) ? theme.surface0
                                                                 : "transparent"
                border.color: (entryMouse.containsMouse || activeFocus) ? theme.amber
                                                                        : "transparent"
                border.width: 1

                Accessible.role: Accessible.MenuItem
                Accessible.name: modelData.label

                Label {
                    anchors.left: parent.left
                    anchors.leftMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    text: entry.modelData.label
                    color: theme.text
                    font.pixelSize: 13
                }

                MouseArea {
                    id: entryMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: menu._choose(entry.modelData.key)
                }

                Keys.onDownPressed:    { event.accepted = true; menu._step(entry.index, 1) }
                Keys.onUpPressed:      { event.accepted = true; menu._step(entry.index, -1) }
                Keys.onReturnPressed:  { event.accepted = true; menu._choose(entry.modelData.key) }
                Keys.onEnterPressed:   { event.accepted = true; menu._choose(entry.modelData.key) }
                Keys.onSpacePressed:   { event.accepted = true; menu._choose(entry.modelData.key) }
                Keys.onTabPressed:     { event.accepted = true; menu._leave(true) }
                Keys.onRightPressed:   { event.accepted = true; menu._leave(true) }
                Keys.onBacktabPressed: { event.accepted = true; menu._leave(false) }
                Keys.onLeftPressed:    { event.accepted = true; menu._leave(false) }
                Keys.onEscapePressed: {
                    event.accepted = true
                    menu.close()
                    if (menu.opener)
                        menu.opener.forceActiveFocus(Qt.OtherFocusReason)
                }
            }

            model: menu._entries
        }
    }
}
