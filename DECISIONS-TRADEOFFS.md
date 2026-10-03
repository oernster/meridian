# Decisions and trade-offs

The deliberate choices Meridian rests on: what was chosen, what was given up
for it and why. Each entry is the decision as the product makes it today.
The detail behind each one, with the tests that hold it, lives in
[ARCHITECTURE.md](ARCHITECTURE.md) and [TESTING.md](TESTING.md);
[TECH_DEBT.md](TECH_DEBT.md) holds what only looks like debt and is left alone
on purpose.

## The product as a whole

### The reference client for MMSP that reads the older formats too

Meridian is the working client for the MMSP protocol and its MFEED format. It
also reads RSS, Atom, podcast feeds and YouTube channel feeds.

- **Rather than:** an MFEED-only reader.
- **Gains:** one application covers everything a reader already subscribes to
  while MFEED adoption grows; publishers have a client to read an MFEED
  against.
- **Costs:** five parsers to keep rather than one.

### One machine, no account

Subscriptions, items and read state live in a SQLite database in the user's
home folder. There is no account, no sync and no server. Moving to another
machine is an export to JSON and an import on the other side.

- **Rather than:** synchronised reading lists; a hosted or web reader.
- **Gains:** nothing to sign in to and nothing held elsewhere; the reading list
  is a file the reader owns.
- **Costs:** read state does not travel; a phone and a desktop cannot share a
  list.

### Pull only, no notifications

The scheduler polls quietly. New items appear in the list on the next tick or
the next view; nothing pops up.

- **Rather than:** push notifications on new items.
- **Gains:** follows MMSP, which is pull only; a calm reader with no engagement
  pressure.
- **Costs:** nothing tells the reader that something has arrived.

### Two licences plus a commercial one

The model is Apache-2.0 and the interface LGPL-3.0. A commercial licence for
Meridian's own code is offered separately. Four licence files sit at the root;
the GPL text is there because the LGPL incorporates it by reference.

- **Rather than:** one licence for everything.
- **Gains:** the model matches the licence of the MMSP ecosystem it serves; the
  interface carries the same terms as Qt itself.
- **Costs:** two licences to keep straight; a contributor grants a relicensing
  right so that commercial terms remain possible.

## Privacy and the network

### Every outbound call is named

Meridian reaches the network in six places: the feeds subscribed to, the
images and media they point at, Feedly's search, Wikipedia's topic
suggestions, YouTube's embedded player and GitHub's releases. The README and
the Guide name all six.

- **Rather than:** an unqualified "no cloud", which a reading of every outbound
  call showed could not stand.
- **Gains:** the reader can see exactly what leaves the machine and why.
- **Costs:** the list is held by the documents rather than by a test; a new
  outbound call would not fail the suite.

### YouTube plays through Google's own player

A YouTube item loads Google's embedded player inside a built-in browser. That
browser is used for this and for nothing else. Every other item plays locally
through Qt's own media stack; feed HTML never goes through the browser.

- **Rather than:** a playable stream, which YouTube does not offer; widening
  the browser's role to render other content.
- **Gains:** YouTube channels work like any other feed.
- **Costs:** watching a video is visible to Google exactly as in a browser tab.
  The browser is the heaviest component the application ships; the Flatpak
  turns off the browser's own sandbox to run it.

### Update checks: quiet unless there is news

A check runs three seconds after launch and then once a day. Only a published
release can prompt, because the releases endpoint returns nothing else. A
version that cannot be read is never treated as newer. A failed automatic
check says nothing; Help, Check for Updates always answers. A skipped version
never prompts again.

- **Rather than:** no check at all; one that reports every outcome.
- **Gains:** updates are found without nagging; a malformed tag or a
  development build never raises a false prompt.
- **Costs:** one unprompted request a day; an outage is invisible unless the
  reader asks.

### Discovery asks two public services

Searching for feeds by topic asks Feedly's public search. While the reader
types, Wikipedia suggests topics: from the second character, after a quarter
of a second's pause, at most ten, with any earlier request abandoned.

- **Rather than:** leaving every feed to be found and pasted by hand.
- **Gains:** a reader can find feeds without knowing their addresses; no key
  is needed for either service.
- **Costs:** what is typed into the field reaches Wikipedia as it is typed and
  Feedly on search. Feedly indexes RSS, Atom and podcasts only, so no MFEED
  feed can be discovered.

### The specification and donations go through the browser

The specification and donate buttons hand an address to the desktop and stop
there. If the desktop refuses, the window says which page it could not open.
The addresses live in one place in Python; the interface never holds a copy.

- **Rather than:** fetching either page inside the application.
- **Gains:** neither button adds a seventh way out of the machine.
- **Costs:** Meridian never learns what happened next.

### A neutral sample reading list

The repository ships a small list of institutional feeds as the worked example
of the export format.

- **Rather than:** a real export of somebody's own subscriptions.
- **Gains:** discloses nothing about anyone; does not go stale with one
  person's tastes.
- **Costs:** none recorded.

## Feeds and polling

### A plain HTTP feed is allowed; what it points at is not

A feed address may be HTTP or HTTPS; any other scheme is refused. Everything
downstream is stricter: the add field enables Subscribe only for an HTTPS
address and the parsers drop any media, enclosure, thumbnail or transcript
address that is not HTTPS.

- **Rather than:** refusing plain HTTP at the feed itself.
- **Gains:** an imported or discovered reading list keeps loading.
- **Costs:** a plain HTTP feed is still fetched in the clear; one cannot be
  typed in by hand.

### A redirect is followed only to HTTPS

Every hop of a redirect is checked before it is made, for feeds and for
discovery alike; one that points at plain HTTP is refused, so that server is
never contacted. A chain is capped at five hops. A feed that has moved for
good is read from its new address and the move is noted, while the
subscription keeps the address it was given.

- **Rather than:** following any redirect and judging only where it ended,
  which would already have spoken to the plain HTTP server; re-pointing the
  subscription automatically.
- **Gains:** a feed cannot be quietly downgraded to an unencrypted connection;
  a moved feed keeps working without the reader doing anything.
- **Costs:** a feed whose publisher redirects it to plain HTTP stops updating.
  It is retried hourly as a failed poll and the window does not say why.

### A five minute floor under every feed

No feed is asked more often than every five minutes, whatever it requests. A
refusal for asking too often is honoured for as long as the server says; with
no figure given, it waits the floor.

- **Rather than:** polling as often as a feed asks.
- **Gains:** polite to publishers; one named constant governs it.
- **Costs:** a new item can take up to five minutes, plus a tick, to appear.

### Ask only for what changed

Each poll sends back the entity tag and the modification date the server gave
last time; a "not modified" answer ends the poll there.

- **Rather than:** downloading every feed in full on every poll.
- **Gains:** most polls cost the server and the reader almost nothing.
- **Costs:** the polling state has to be stored per feed.

### A failing feed backs off

A feed that has gone is asked again once a day; any other failure waits an
hour. A document over ten megabytes is refused rather than parsed.

- **Rather than:** retrying at the normal pace; parsing whatever arrives.
- **Gains:** a dead or broken feed costs almost nothing; an oversized document
  cannot swamp the reader.
- **Costs:** a feed that recovers can take up to a day to be noticed.

### Polling state kept apart from the subscription

What the reader subscribed to and the operational state of polling it are
stored separately.

- **Rather than:** one record holding both.
- **Gains:** a subscription stays a fixed statement of intent; a feed can be
  added without ever being polled.
- **Costs:** two tables to keep in step.

### The MMSP version stated once and checked against the specification

The protocol version lives in one place. The User-Agent and the parser's
version rule both derive from it: any 1.x document is read and anything else,
including a document that does not say, is refused. Where the specification
repository is checked out alongside, a test holds the rule to its published
schema.

- **Rather than:** a version written into the User-Agent alone; depending on a
  package of schemas that was never going to exist.
- **Gains:** a protocol revision cannot land unnoticed; the client and the
  specification cannot quietly disagree.
- **Costs:** without the sibling checkout the conformance test skips itself,
  saying so only in the skip count.

### One parser per source type

RSS, Atom, podcast, MFEED and platform feeds each have their own parser. A
YouTube channel is an Atom feed. A hook exists for platform adapters; none is
built in, so RSS is always the fallback.

- **Rather than:** one parser for every format.
- **Gains:** each parser mirrors one specification, with one test module each.
- **Costs:** shared behaviour (such as dropping insecure media) is written in
  each.

### XML parsed defensively

Every XML feed is read through a parser hardened against hostile documents.

- **Rather than:** the standard library's parser.
- **Gains:** a malicious feed cannot exhaust the machine through entity
  expansion.
- **Costs:** one more runtime dependency.

## Reading

### Filters hide; they never delete

A filter is an expression in the MMSP grammar, applied each time a feed's list
is read. Every item is still stored. The filter dialog splits an expression
into a row per term that can be switched off; what is left is joined with AND.

- **Rather than:** discarding filtered items as they arrive; a text field of
  raw syntax.
- **Gains:** changing or clearing a filter brings items back; common cases
  need no knowledge of the grammar.
- **Costs:** filtered items still take space; anything beyond AND has to be
  typed as text.

### Duplicates removed as the list is read

Items sharing a canonical address are shown once; so are items sharing an
identifier within a feed.

- **Rather than:** removing duplicates from the store.
- **Gains:** the store keeps what the feed sent.
- **Costs:** the work is repeated on every read.

### Full text where a feed offers it

An RSS item's full content is preferred over its summary.

- **Rather than:** the description alone.
- **Gains:** whole articles read inside Meridian where the publisher allows.
- **Costs:** none recorded.

### Feed HTML is not sanitised

Article HTML is shown through Qt's rich-text engine, which accepts a small
subset of HTML and runs no script. No sanitising pass runs and no sanitiser
is shipped.

- **Rather than:** a sanitising pass over every article.
- **Gains:** one dependency fewer; the protection that exists is the one
  stated.
- **Costs:** whatever the engine accepts is shown as the feed sent it. Adding
  a sanitiser is a decision still open.

## The interface

### Pictures rather than emoji

Every button on the two bands is a mark drawn from a file. Its words are a
tooltip that opens on hover and on keyboard focus alike; the same words name
it for assistive technology.

- **Rather than:** emoji, which each platform's font draws differently.
- **Gains:** the same window on Windows, macOS and Linux; the focus ring reads
  without a mouse.
- **Costs:** every mark has to be generated and kept in step with its master.

### Two bands with different jobs

The header holds what acts on reading: import, export, search, manage, the
specification, the theme and Help. The strip at the foot holds donate and the
two licences. The foot's marks are two thirds of the header's, taken from the
header's own size.

- **Rather than:** every button in the header.
- **Gains:** the header stays about reading; the lighter foot does not weigh
  the window down; the two sizes cannot drift apart.
- **Costs:** two places to look.

### A Help menu rather than a menu bar

Help drops a small menu: the Guide, Check for Updates and About Meridian.

- **Rather than:** a full menu bar; the update check inside About.
- **Gains:** the check sits where the rest of the portfolio keeps it; the
  window stays uncluttered.
- **Costs:** none recorded.

### Everything on the keyboard

Tab and Shift+Tab wrap through the whole window, every drawer and every
dialog; arrows move along bands, chips, lists and dialog footers; Escape
closes. Nothing wears a focus ring until the first Tab. Each handover between
components is tested with real keys through a real window.

- **Rather than:** mouse-first controls.
- **Gains:** the whole application works without a mouse; a missed connection
  fails the suite rather than compiling silently.
- **Costs:** every new control needs its place in the ring. Two buttons still
  answer Space but not Enter; that is recorded as a defect.

### Long text reads itself

The Guide, both licences and the address list shown before a bulk subscribe
scroll gently on their own: hold, descend, hold, rewind, repeat. Touching the
surface suspends the cycle and it resumes where the reader left it. One
component carries the pace for the whole application.

- **Rather than:** static pages; the same motion on every list.
- **Gains:** long text can be read hands free. The article pane and the lists
  are declined on purpose, being places to set one's own pace or to act.
- **Costs:** none recorded.

### A reading dialog opens on Close

The Guide and the licences share one dialog. It opens with Close focused; the
page is a Tab stop only while it overflows and never takes focus from a click.

- **Rather than:** opening focused on the text.
- **Gains:** Enter or Escape closes at once; a click on the words leaves focus
  where it was.
- **Costs:** none recorded.

### The Guide names every control

The Guide lists every button on both bands beside the mark it draws. A button
with no line in the Guide fails the suite, as does a line naming a mark with
no file.

- **Rather than:** a guide written by hand and left to drift.
- **Gains:** the Guide cannot fall behind the window.
- **Costs:** every new button needs its Guide line before the suite passes.

### Removal always asks; the count is the selection

Removing a feed, singly or in bulk, opens a confirmation owned by the window;
the sidebar and the context menu only report the request. The manager's
selection is keyed by feed, never by the row on screen.

- **Rather than:** a selection tied to rows, which scrolling silently emptied.
  Measured on two hundred feeds, select all then scroll left 113 selected; the
  dialog said 113 and deleted 113.
- **Gains:** what the confirmation counts is what the reader chose.
- **Costs:** none recorded.

### Removal keeps the place in the list

Removed feeds are taken out of the list row by row.

- **Rather than:** rebuilding the whole list.
- **Gains:** the scroll position survives a bulk removal.
- **Costs:** none recorded.

### Two themes, one toggle

Catppuccin Mocha and Latte, switched by one button. The choice is remembered,
as are the volume and a skipped update, in Qt's own settings on the interface
side.

- **Rather than:** following the system theme; settings held in the Python
  side.
- **Gains:** the Python side stays stateless between checks.
- **Costs:** a reader who wants the system's choice switches by hand.

## Building and installing

### Installed for one user, without administrator rights

On Windows the setup program installs into the user's own folders and
registers under the user's own registry hive.

- **Rather than:** a machine-wide install.
- **Gains:** no administrator prompt.
- **Costs:** each account on a machine installs separately.

### A setup program of its own

Install, upgrade, repair and removal are one bespoke program. Everything that
touches the machine is kept free of Qt in its own package, which is inside the
coverage gate; the window around it is not.

- **Rather than:** a generic installer.
- **Gains:** the operations are tested like the application.
- **Costs:** the setup program is Meridian's own to maintain.

### Uninstalling removes the reader's data too

Removing Meridian through the setup program takes the reading list with it:
the database folder in the home folder goes along with the application and
its per-user data and cache folders. The confirmation says so before anything
is removed. Started with `--keep-user-data`, the setup program removes the
application and leaves the data where it is.

- **Rather than:** leaving the database behind for a later reinstall to find.
- **Gains:** an uninstall does not leave the reading list behind; the
  confirmation's promise is kept.
- **Costs:** subscriptions and read state are gone unless they were exported
  first. The window offers no way to keep them.

### An upgrade never leaves the reader with nothing

The old installation is moved aside, the new one put in its place and the old
one deleted only once the new one is there. If the swap fails the old one is
put back; if that fails too, the old copy is kept rather than deleted.

- **Rather than:** overwriting in place.
- **Gains:** a failed upgrade is a failed upgrade, not a lost application.
- **Costs:** a failed rollback can leave a backup folder behind.

### Launch when finished

A box ticked by default starts Meridian after an install, upgrade, reinstall
or repair. The setup program waits up to fifteen seconds for the window, brings
it to the front, then closes. The decision to launch is a tested function; the
act is not.

- **Rather than:** leaving the reader to find a shortcut.
- **Gains:** the application arrives in front rather than flashing on the
  taskbar, which is what Windows does to a window whose starter has gone.
- **Costs:** the launch itself is checked only by hand.

### The progress bar always moves

Every operation reports a percentage. The bar runs indeterminate from the
moment work starts until the first figure arrives.

- **Rather than:** status text alone, which left repair and removal running
  behind an empty bar.
- **Gains:** a stage with nothing to measure still shows movement.
- **Costs:** none recorded.

### macOS builds are notarised or not released

The macOS build refuses to proceed without notarisation credentials, checked
before any build work. Both the application and the disk image are notarised
and stapled, then checked as an end user's machine would. Building without
notarisation needs an explicit switch and is labelled unreleasable. The
keychain profile is named outright.

- **Rather than:** skipping notarisation quietly when credentials were absent,
  which shipped disk images no other Mac would open.
- **Gains:** a published disk image opens; the copied-out application works
  offline.
- **Costs:** an Apple developer account and a keychain profile on the build
  machine.

### The Flatpak build installs what it made

The Linux script builds the bundle then reinstalls it over any copy of the
same version.

- **Rather than:** ending with instructions to install by hand.
- **Gains:** one command from source to a running application.
- **Costs:** the build replaces whatever version was installed.

### Every build bundles the same licences

One list names the licence texts and every delivery script reads it; a test
holds them to it.

- **Rather than:** each script naming its own files.
- **Gains:** a build cannot silently ship without a licence, which the
  application would otherwise show only as "unavailable".
- **Costs:** none recorded.

### One home for the version

The root VERSION file holds the only copy of the version. The package, the
packaging metadata and the build scripts read it; the website is stamped from
it. The stamper also links each stylesheet and script by a hash of its content.

- **Rather than:** a version written into source.
- **Gains:** a release is one edit and one script; a browser never pairs a new
  page with a cached old stylesheet.
- **Costs:** the website has to be stamped after each change.

### Generated icons, tracked marks

The application icons are generated from one master and not tracked. The
button marks are generated the same way but tracked, because the interface
reads them at run time from a source checkout.

- **Rather than:** tracking every generated file; generating the marks before
  every run.
- **Gains:** one master per picture; a checkout runs without a build step.
- **Costs:** a test has to hold the tracked marks to what the generator would
  produce.

## Engineering

### Layers with one place where they meet

The code is split into domain, application, infrastructure and interface,
each allowed to depend only inward. A structural test scans every import.
Constructors take their dependencies; one composition root wires them.

- **Rather than:** convention alone; a dependency injection framework or
  module-level singletons.
- **Gains:** the rules about feeds and filters are tested with no disk,
  network or screen.
- **Costs:** more modules and more explicit wiring.

### Complete coverage, including the interface bridge

Branch coverage must be total over the application package (its bridge to the
interface included) and over the setup program's operations. Seven exclusions
are named with their reasons: the composition root, four installer functions
that would act on the developer's own machine and two branches only a broken
system reaches.

- **Rather than:** leaving the interface layer out, as most of the portfolio
  does.
- **Gains:** anything short of complete is a decision nobody made.
- **Costs:** the bridge tests are a large part of the suite; the excluded
  functions are checked only by hand.

### Small files, the interface and the tests included

No Python module, QML component, test or installer file may pass four hundred
lines; one in the last twentieth below the cap fails too, so a file near it is
cut well below rather than shaved. The build scripts are exempt from length,
never from the formatters.

- **Rather than:** a cap on the package alone, which left the QML and the
  tests free to grow without limit.
- **Gains:** modules split at real seams; splitting the large QML files
  turned up repetition that became shared components.
- **Costs:** many small files and more wiring between them.

### Formatting checked by the suite

Black and flake8 run as assertions inside the test suite over every Python
file, delivery scripts included.

- **Rather than:** a hook or a separate step.
- **Gains:** formatting is not optional; a build script cannot drift unseen.
- **Costs:** a formatting slip fails the whole run.

### QML is compiled by the suite

Every QML file is compiled as a test.

- **Rather than:** the QML linter, which reports hundreds of warnings inherent
  to this front end and exits cleanly regardless.
- **Gains:** a syntax error, a missing property or an unresolvable component
  fails the suite.
- **Costs:** compiling cannot catch an input a component reads from outside
  itself; each extracted component also gets a test built with no caller in
  scope.

### Tests with real parts

Qt is never mocked. The suite forces the offscreen platform before any Qt
import, so no window appears; the real main window is built against
hand-written stub controllers. HTTP is answered inside the process; the
database is a temporary file. Rows are clicked with a real mouse as well as
walked with keys.

- **Rather than:** mocked widgets; keyboard tests standing in for the mouse.
  Four green keyboard rings once hid rows that did nothing when clicked.
- **Gains:** a passing test means the real window works.
- **Costs:** stubs are written and kept by hand; the services below the
  bridge are still tested with mocks.

### A background thread never holds the interface

The update check's worker holds only the service and a result to fill. The
controller collects finished results on the interface thread with its own
timer.

- **Rather than:** a worker that closed over the controller, which crashed when
  the controller was dropped mid-check.
- **Gains:** a controller can be released at any moment; measured over 360
  shutdown runs, none crashed.
- **Costs:** a polling timer where a direct signal would otherwise do.

### A guard is trusted only once it has failed

Every structural test and every fix is proved by planting the violation and
watching it fail before the tree is restored.

- **Rather than:** assuming a guard bites.
- **Gains:** a green suite is known to mean something.
- **Costs:** every guard costs a proof as well as a test.
