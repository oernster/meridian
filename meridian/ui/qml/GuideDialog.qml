import QtQuick
import QtQuick.Controls

// The Guide: what the screen cannot say for itself.
//
// Ported from ClearBudget's How It Works. Two jobs, in this order. It NAMES the
// furniture, each entry led by the real mark its button draws, because every
// control on the two bands is a picture with no word beside it. Then it states
// the few rules the lists depend on that no screen can show: how often a feed
// is asked, what a filter does and what leaves the machine.
//
// Every entry carries the REAL mark, the same file the button loads, never a
// description in words or a look-alike glyph: an icon guide showing something
// other than the icon is worse than no guide. A structural test holds the two
// bands and this page to the same set of marks, so a button added to either
// band without a line here fails the suite.
//
// It is deliberately short. A help screen nobody finishes explains nothing, so
// anything a control says for itself (its tooltip) is left to the control.
//
// The chrome, the self-reading page and the focus rules (opens on Close; the
// page a Tab stop only while it overflows, never taking a click) are
// ReadingDialog's.
ReadingDialog {
    id: root
    width: 640
    height: Math.min(640, Overlay.overlay ? Overlay.overlay.height - _margin * 2 : 640)
    namePrefix: "guide"
    heading: "Guide"
    body: guideHtml
    bodyFormat: TextEdit.RichText
    bodyColor: theme.subtext
    bodyPadding: 18

    readonly property int _margin: 20

    // Height of a mark in the text. Bigger than the words around it on
    // purpose: this page is read to IDENTIFY a picture. ClearBudget's value,
    // for the same reason.
    readonly property int _markPx: 30

    function _mark(file) {
        return "<img src=\"" + Qt.resolvedUrl("art/" + file) + "\" width=\""
               + root._markPx + "\" height=\"" + root._markPx
               + "\" style=\"vertical-align: middle\"> "
    }

    function _row(file, name, text) {
        return "<p>" + root._mark(file) + "<b>" + name + "</b>: " + text + "</p>"
    }

    // Built once per palette so the headings follow the theme.
    readonly property string guideHtml: {
        var headStyle = "style=\"color: " + root.theme.text + "\""
        return ""
        + "<h2 " + headStyle + ">How Meridian Works</h2>"

        + "<h3 " + headStyle + ">Along the top</h3>"
        + root._row("import.png", "Import",
                    "subscriptions from a Meridian JSON file.")
        + root._row("export.png", "Export",
                    "every subscription to a JSON file you keep. Import and "
                    + "export are how a reading list moves to another machine; "
                    + "there is no sync.")
        + root._row("search.png", "Find feeds",
                    "search by topic, with topics suggested as you type. Tick "
                    + "the results you want and subscribe to them together. The "
                    + "search covers RSS, Atom and podcast sources, so an MFEED "
                    + "is added by its address instead.")
        + root._row("manage.png", "Manage subscriptions",
                    "add a feed by its https:// address, change an address, set "
                    + "a filter or remove feeds, one at a time or ticked "
                    + "together.")
        + root._row("specification.png", "Specification",
                    "the MMSP specification, opened in your browser.")
        + root._row(root.theme.isDark ? "light-mode.png" : "dark-mode.png",
                    "Light or dark",
                    "switch palette. The mark shows the palette you would switch "
                    + "TO; the choice is kept for next time.")
        + root._row("help.png", "Help",
                    "this Guide, then About Meridian, which also holds the "
                    + "manual check for updates.")
        + "<p>Hover any button (or reach it with Tab) to see its name.</p>"

        + "<hr><h3 " + headStyle + ">Along the foot</h3>"
        + root._row("donate.png", "Donate",
                    "buy the author a drink. It opens a donation page in your "
                    + "browser; Meridian opens no connection of its own for it "
                    + "and nothing is held back behind it.")
        + root._row("ui-licence.png", "UI licence",
                    "the interface's licence, LGPL-3.0.")
        + root._row("model-licence.png", "Model licence",
                    "the model's licence, Apache-2.0.")

        + "<hr><h3 " + headStyle + ">Reading</h3>"
        + "<p>Feeds sit on the left, the chosen feed's items in the middle and "
        + "the item itself on the right. Opening an item marks it read; Mark "
        + "all read does the whole feed. The chips above each list sort it: "
        + "feeds by name either way or by unread count, items newest first, "
        + "oldest first or by title.</p>"
        + "<p>Tick feeds to remove several at once; right-click one to "
        + "remove just that feed. Either way you are asked first, since its "
        + "downloaded items go with it. Podcast and video items play in the "
        + "built-in player. A YouTube item plays in YouTube's own embedded "
        + "player, which Google can see exactly as it would in a browser "
        + "tab.</p>"

        + "<hr><h3 " + headStyle + ">Three rules behind the lists</h3>"
        + "<p><b>A feed is asked at most once every five minutes.</b> It is "
        + "asked less often if the feed wants that. A feed that says it is "
        + "busy is left alone for as long as it asks, five minutes at the "
        + "least. Each visit tells the server what was seen last "
        + "time, so an unchanged feed sends nothing back. New items appear "
        + "on the next visit; nothing is pushed.</p>"
        + "<p><b>A filter hides, it never deletes.</b> Set one on a feed in "
        + "Manage subscriptions. Its dialog lists the terms already there as "
        + "rows you can switch on and off, so the common cases need no "
        + "syntax. Clear the filter and every item is back.</p>"
        + "<p><b>Your reading stays on this machine.</b> Subscriptions and "
        + "read state live in one local database. Meridian goes online only "
        + "to fetch your feeds and what they point at, to search when you "
        + "find feeds, to suggest topics as you type, to play a YouTube item "
        + "and to ask GitHub, just after launch and then once a day, whether "
        + "a newer Meridian exists. "
        + "A feed you add by hand must be an https:// address.</p>"

        + "<hr><h3 " + headStyle + ">Keyboard</h3>"
        + "<p>Tab moves forward and Shift+Tab back through every control, "
        + "wrapping at both ends; along the top and the foot, Right and Left "
        + "do the same. Up and Down walk a list and the Help menu. Space "
        + "presses the focused control and Escape closes a drawer, a dialog "
        + "or a menu. Nothing is highlighted until your first keypress; a "
        + "dialog opens on its first control.</p>"
    }
}
