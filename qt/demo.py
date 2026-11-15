"""A small batch uploader that shows every widget of quiet_ui.py. The data is made up.

    python demo.py                 open the demo window
    python demo.py --shots DIR     save screenshots to DIR (rendered off screen)

Set QUIET_QT=pyqt5 or QUIET_QT=pyside6 to pick the Qt binding.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ARGS = argparse.ArgumentParser(description=__doc__.splitlines()[0])
ARGS.add_argument("--shots", metavar="DIR", help="save screenshots to DIR and exit")
OPTIONS = ARGS.parse_args()
# --shots renders hidden windows (WA_DontShowOnScreen) on the normal platform: Qt's "offscreen"
# platform has no system fonts on Windows. On a Linux server without a display, run it under xvfb-run.

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quiet_ui as q  # noqa: E402
from quiet_ui import (  # noqa: E402
    QT_API, TOKENS, QHBoxLayout, QLineEdit, QMessageBox, QPlainTextEdit, QTimer, QVBoxLayout, QWidget, Qt,
    rough_duration, short_id,
)

STEPS = ["Read", "Check", "Upload", "Verify"]
DOING = {"Read": "Reading…", "Check": "Checking…", "Upload": "Uploading…",
         "Verify": "Verifying…"}
SECONDS_PER_FILE = 3

# name, id, size, state, step, result
SAMPLE = [
    ("team-photo.png", "c41e9a07d2b8f13e66d0", "4.8 MB", "done", 3, "Done · 4.8 MB"),
    ("invoice-0193.pdf", "7b20e55f19ac04d3e2a9", "220 KB", "done", 3, "Done · 220 KB"),
    ("notes.md", "e8f1036bb4c7d9a2150e", "18 KB", "done", 3, "Done · 18 KB"),
    ("backup-2026-11.tar", "2d9b7c44a01fe6835bc7", "1.1 GB", "failed", 1, "File changed while it was read"),
    ("archive.zip", "5a6c18f3e92b07d4a1ce", "640 MB", "running", 3, ""),
    ("photos/IMG_0412.jpg", "91fe2a07c3d5b8e46f10", "3.2 MB", "waiting", 0, "starts in 85 s"),
    ("design-review.fig", "3be47d10a96c2f58e01d", "3.1 MB", "running", 2, "1.2 / 3.1 MB"),
]


def size_line(item_id: str, size: str) -> str:
    return f"{short_id(item_id)} · {size}"


# ---------------------------------------------------------------------------
# Run page
# ---------------------------------------------------------------------------
class RunPage(q.Page):
    def __init__(self, win: "DemoWindow"):
        super().__init__("Run", "Upload saved files to the server, then read each one back to check it.")
        self.win = win
        self.add_action(q.button("Show an error", "ghost", on_click=self.show_error))
        self.run_btn = self.add_action(q.button("Start run", "primary", "play", on_click=self.toggle))

        self.stat_total = q.Stat("Total", TOKENS["win"])
        self.stat_done = q.Stat("Completed", TOKENS["good"])
        self.stat_failed = q.Stat("Failed", TOKENS["bad"])
        self.stat_busy = q.Stat("In progress", TOKENS["warn"])
        self.body.addLayout(q.stats_row([self.stat_total, self.stat_done, self.stat_failed, self.stat_busy]))
        self.body.addSpacing(22)

        top = QHBoxLayout()
        self.progress_label = q.label("Ready to start", "RowLabel")
        self.progress_count = q.label("", "CountText")
        top.addWidget(self.progress_label)
        top.addStretch()
        top.addWidget(self.progress_count)
        self.body.addLayout(top)
        self.body.addSpacing(8)
        self.progress = q.QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.body.addWidget(self.progress)
        self.body.addSpacing(8)
        meta = QHBoxLayout()
        self.elapsed = q.label("", "MetaText")
        self.end_line = q.label("", "MetaText")
        meta.addWidget(self.elapsed)
        meta.addStretch()
        meta.addWidget(self.end_line)
        self.body.addLayout(meta)
        self.body.addSpacing(22)

        bar = QHBoxLayout()
        self.tabs = q.Segmented(["Items", "Log"], tabs=True)
        bar.addWidget(self.tabs, 1)
        bar.addWidget(q.button("Clear", "ghost", "trash", on_click=self.clear))
        self.body.addLayout(bar)
        self.body.addSpacing(6)
        self.body.addWidget(q.Divider())
        self.views = q.QStackedWidget()
        self.items = q.ItemList("Files show here once you start a run.")
        self.log = q.log_view()
        self.views.addWidget(self.items)
        self.views.addWidget(self.log)
        self.tabs.changed.connect(self.views.setCurrentIndex)
        self.body.addWidget(self.views, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(700)
        self.timer.timeout.connect(self.tick)
        self.seconds = 0
        self.stopping = False
        self.load_sample()

    # -- sample data and the fake run ---------------------------------------------------------
    def load_sample(self) -> None:
        self.items.clear()
        self.model = []
        for name, item_id, size, state, at, result in SAMPLE:
            row = self.items.add(q.ItemRow(name, size_line(item_id, size)))
            self.model.append({"row": row, "size": size, "state": state, "at": at, "result": result})
            self.paint(self.model[-1])
        self.log.setPlainText("\n".join([
            "12:04:31  run started: 14 files, 4 at a time",
            "12:04:33  notes.md uploaded and verified (18 KB)",
            "12:04:40  invoice-0193.pdf uploaded and verified (220 KB)",
            "12:05:02  backup-2026-11.tar failed at Check: file changed while it was read",
            "12:05:17  team-photo.png uploaded and verified (4.8 MB)",
        ]))
        self.seconds = 192
        self.refresh()

    def paint(self, item: dict) -> None:
        state, at = item["state"], item["at"]
        status = DOING[STEPS[at]] if state == "running" else None
        item["row"].set_progress(STEPS, at, state, status=status, result=item["result"])

    def refresh(self) -> None:
        done = sum(1 for m in self.model if m["state"] == "done")
        failed = sum(1 for m in self.model if m["state"] == "failed")
        busy = sum(1 for m in self.model if m["state"] in ("running", "waiting"))
        total = max(1, len(self.model))
        self.stat_total.set_value(len(self.model))
        self.stat_done.set_value(done)
        self.stat_failed.set_value(failed)
        self.stat_busy.set_value(busy)
        finished = done + failed
        self.progress.setValue(int(100 * finished / total))
        self.progress_label.setText(f"Uploading {finished} of {total}" if busy else "Finished")
        self.progress_count.setText(f"{int(100 * finished / total)}%")
        self.elapsed.setText(f"Elapsed {self.seconds // 60:02d}:{self.seconds % 60:02d}")

    def tick(self) -> None:
        self.seconds += 1
        moving = [m for m in self.model if m["state"] in ("running", "waiting")]
        if not moving or self.stopping:
            self.finish()
            return
        m = moving[0]
        if m["state"] == "waiting":
            m["state"], m["at"], m["result"] = "running", 0, ""
        elif m["at"] < len(STEPS) - 1:
            m["at"] += 1
        else:
            m["state"], m["result"] = "done", f"Done · {m['size']}"
            self.log.appendPlainText(f"{m['row'].name.text()} uploaded and verified ({m['size']})")
        self.paint(m)
        self.refresh()

    def toggle(self) -> None:
        if self.timer.isActive():
            box = QMessageBox(self)
            box.setWindowTitle("Stop the run?")
            box.setText("Files that are uploading finish first. The rest are not started.")
            stop = box.addButton("Stop", QMessageBox.AcceptRole)
            box.addButton("Keep going", QMessageBox.RejectRole)
            q.run_dialog(box)
            if box.clickedButton() is stop:
                self.stopping = True
                self.run_btn.setEnabled(False)
                self.win.set_status("Stopping…", "warn")
            return
        dialog = make_start_dialog(self.win)
        if q.run_dialog(dialog):
            self.start()

    def start(self) -> None:
        self.stopping = False
        self.end_line.setText("")
        q.set_button_kind(self.run_btn, "danger", "stop")
        self.run_btn.setText("Stop")
        self.win.set_status("Running", "good")
        self.timer.start()

    def finish(self) -> None:
        self.timer.stop()
        done = sum(1 for m in self.model if m["state"] == "done")
        failed = sum(1 for m in self.model if m["state"] == "failed")
        not_done = len(self.model) - done - failed
        line = f"uploaded {done}/{len(self.model)} · {failed} failed"
        if not_done:
            line += f" · {not_done} not done (stopped)"
        self.end_line.setText(line)
        self.log.appendPlainText(line)
        self.run_btn.setEnabled(True)
        q.set_button_kind(self.run_btn, "primary", "play")
        self.run_btn.setText("Start run")
        self.win.set_status("Idle")

    def clear(self) -> None:
        self.items.clear()
        self.log.clear()
        self.model = []
        self.progress.setValue(0)
        self.progress_label.setText("Ready to start")
        self.progress_count.setText("")
        self.end_line.setText("")
        for s in (self.stat_total, self.stat_done, self.stat_failed, self.stat_busy):
            s.set_value(0)

    def show_error(self) -> None:
        self.win.show_error(
            "Upload failed",
            "The server is limiting requests from this connection (HTTP 429: too many requests). "
            "Wait a minute and start again, or lower At the same time in Settings.")


# ---------------------------------------------------------------------------
# Settings page
# ---------------------------------------------------------------------------
class SettingsPage(q.Page):
    def __init__(self):
        super().__init__("Settings", "Uploads, pacing and network. Changes are saved to settings.ini.")
        self.save_btn = q.button("Save changes", "primary", on_click=self.save)
        self.state = q.SaveState(self.save_btn)
        self.state.issue_clicked.connect(lambda _issue: self.destination.setFocus())
        self.add_action(self.state)
        self.add_action(q.button("Reload", "secondary", on_click=self.reload,
                                 tooltip="Discard changes and read settings.ini again"))
        self.add_action(self.save_btn)

        uploads = q.SettingsSection("Uploads", "Where files go and how many at once")
        self.destination = QLineEdit("archive/2026")
        self.destination.setPlaceholderText("Folder on the server")
        uploads.add_row("Destination", "Server folder for new files", self.destination)
        self.workers = q.NoWheelSpinBox(1, 64, 4)
        uploads.add_row("At the same time", "Files uploading at once", self.workers)
        self.verify = q.ToggleSwitch(True)
        self.verify_row = uploads.add_row("Check after upload", "", self.verify)
        self.limit = q.NoWheelDoubleSpinBox(0, 1000, 2.0, 1, " GB")
        self.limit.setSpecialValueText("No limit")
        uploads.add_row("Skip files larger than", "0 = no limit", self.limit)

        pacing = q.SettingsSection("Pacing", "Spread uploads so the server is not flooded")
        self.spread = q.DurationInput(1800)
        pacing.add_row("Spread over", "The whole run takes this long", self.spread)
        self.pause = q.RangeInput(2, 8, "seconds")
        pacing.add_row("Pause between files", "A random pause in this range", self.pause)
        self.order = q.NoWheelComboBox(["Newest first", "Oldest first", "Random order"])
        pacing.add_row("Order", "Which files go first", self.order)

        mix = q.SettingsSection("Priority mix", "Share of files per priority")
        bar_box = QWidget()
        bl = QVBoxLayout(bar_box)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(10)
        colors = q.DistributionBar.COLORS
        bar = q.DistributionBar([(20, colors[0]), (30, colors[1]), (50, TOKENS["off"])])
        bl.addWidget(bar)
        bl.addWidget(q.legend([("High · 20%", colors[0]), ("Normal · 30%", colors[1]),
                               ("Low · the rest", TOKENS["off"])]))
        mix.add_row("Mix", "High-priority files go first, low ones fill the gaps", bar_box, stacked=True)

        connection = q.SettingsSection("Connection")
        self.proxy = q.ToggleSwitch(False)
        self.proxy_row = connection.add_row("Use a proxy", "", self.proxy)
        proxies = QPlainTextEdit()
        proxies.setPlaceholderText("host:port, one per line")
        proxies.setFixedHeight(96)
        connection.add_row("Proxy list", "Used in turn; a broken one is skipped", proxies, stacked=True)
        connection.add_row("Timeout", "How long one request may take", q.NoWheelSpinBox(1, 300, 20, " s"))

        schedule = q.SettingsSection("Schedule", "Run uploads on their own")
        schedule.add_row("Every day at", "Local time", QLineEdit("02:30"))
        schedule.add_row("Only on mains power", "Skip runs on battery", q.ToggleSwitch(True))

        advanced = q.SettingsSection("Advanced")
        advanced.add_row("Retries", "Tries per file before it counts as failed", q.NoWheelSpinBox(0, 10, 2))
        advanced.add_row("Log level", "", q.NoWheelComboBox(["Normal", "Detailed", "Errors only"]))

        cats = q.CategoryView()
        cats.add("General", "sliders", [uploads, pacing, mix])
        cats.add("Network", "globe", [connection])
        cats.add("Schedule", "chart", [schedule])
        cats.add("Advanced", "gear", [advanced])
        self.body.addWidget(cats, 1)

        self.loading = False
        for signal in (self.destination.textChanged, self.workers.valueChanged, self.verify.toggled,
                       self.limit.valueChanged, self.spread.changed, self.pause.changed,
                       self.order.currentIndexChanged, self.proxy.toggled):
            signal.connect(lambda *_: self.changed())
        self.show_states()
        self.state.set_dirty(False)

    def show_states(self) -> None:
        """A help line that tells the current state: --good when on, --warn when off matters."""
        on = self.verify.isChecked()
        self.verify_row.help.setText("On: every file is read back and compared" if on
                                     else "Off: files are not checked after upload")
        self.verify_row.help.show()
        q.set_state(self.verify_row.help, "on" if on else "off")
        self.proxy_row.help.setText("On: requests go through the list below" if self.proxy.isChecked()
                                    else "Off: connects directly")
        self.proxy_row.help.show()

    def changed(self) -> None:
        self.show_states()
        issues = [] if self.destination.text().strip() else [("destination", "Destination is empty")]
        self.destination.setProperty("invalid", bool(issues))
        q.repolish(self.destination)
        self.state.set_issues(issues)
        self.state.set_dirty(True)

    def save(self) -> None:
        self.state.flash_saved()

    def reload(self) -> None:
        self.state.set_issues([])
        self.state.set_dirty(False)


# ---------------------------------------------------------------------------
# Start run: the stepped popup
# ---------------------------------------------------------------------------
def make_start_dialog(parent: QWidget | None = None) -> q.StepDialog:
    dialog = q.StepDialog("Start run", finish_text="Start run", parent=parent)
    totals = (120, 1000)

    # Step 1: what to do
    page1 = QWidget()
    v = QVBoxLayout(page1)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    grid = q.form_grid()
    files = q.Segmented([f"New files · {totals[0]:,}", f"Saved files · {totals[1]:,}"], index=1)
    action = q.Segmented(["Upload", "Check only"])
    count = q.CountOf(totals[1], "saved files", 500)
    spread_on = q.ToggleSwitch(True)
    spread = q.DurationInput(1800)
    spread_note = q.label("", "Note")
    spread_row = QHBoxLayout()
    spread_row.setSpacing(12)
    spread_row.addWidget(spread_on)
    spread_row.addWidget(spread)
    spread_row.addWidget(spread_note)
    spread_row.addStretch()
    grid.addWidget(q.form_label("Files"), 0, 0)
    grid.addWidget(files, 0, 1, Qt.AlignLeft)
    grid.addWidget(q.form_label("Action"), 1, 0)
    grid.addWidget(action, 1, 1, Qt.AlignLeft)
    grid.addWidget(q.form_label("How many"), 2, 0)
    grid.addWidget(count, 2, 1, 1, 2)
    grid.addWidget(q.form_label("Spread over"), 3, 0)
    grid.addLayout(spread_row, 3, 1, 1, 2)
    v.addLayout(grid)
    block, summary = q.summary_block("THIS RUN")
    v.addWidget(block)
    v.addStretch()
    dialog.add_step("What to do", page1, "Start a run", "What should this run do?", "play")

    # Step 2: details
    page2 = QWidget()
    destination = q.LookupField("archive/2026", "Folder on the server")
    destination.lookup.connect(lambda text: destination.found(
        "@" + text.split("/")[0], f"{short_id('Ab12c9e0f4d7a35b88xY9z')} · 1,204 files",
        edit_tip="Change the destination"))
    destination.lookup.emit(destination.text())
    workers = QWidget()
    wl = QHBoxLayout(workers)
    wl.setContentsMargins(0, 0, 0, 0)
    wl.setSpacing(12)
    workers_spin = q.NoWheelSpinBox(1, 64, 4)
    workers_spin.setFixedWidth(120)
    auto = q.ToggleSwitch(False)
    wl.addWidget(workers_spin)
    wl.addWidget(auto)
    wl.addWidget(q.label("Automatic", "Note"))
    wl.addStretch()
    takes = q.label("", "MonoValue")
    page2.setLayout(q.detail_grid([
        ("Destination", "Every file goes here", destination),
        ("At the same time", "Files uploading at once", workers),
        ("Takes about", "To upload all of them", takes),
    ]))
    dialog.add_step("Details", page2, "Details", "Where the files go, and how fast.", "sliders")

    # Step 3: confirm
    page3 = QWidget()
    p3 = QVBoxLayout(page3)
    p3.setContentsMargins(0, 0, 0, 0)
    p3.setSpacing(6)
    p3.addWidget(q.label("Access key", "RowLabel"))
    key_row = QHBoxLayout()
    key_row.setSpacing(6)
    key = QLineEdit()
    key.setEchoMode(QLineEdit.Password)
    key.setPlaceholderText("Access key — kept in memory for this run only")
    show = q.button("Show", "ghost")
    show.setCheckable(True)
    show.toggled.connect(lambda on: (key.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password),
                                     show.setText("Hide" if on else "Show")))
    key_row.addWidget(key, 1)
    key_row.addWidget(show)
    p3.addLayout(key_row)
    p3.addWidget(q.label("The key of the account that owns the destination.", "Note"))
    p3.addSpacing(14)
    size_row = QHBoxLayout()
    size_row.addWidget(q.label("Upload size", "RowLabel"), 1)
    size_value = q.label("", "MonoValue")
    size_row.addWidget(size_value)
    p3.addLayout(size_row)
    p3.addSpacing(14)
    settings_row = QHBoxLayout()
    settings_row.addWidget(q.label("Retries and pacing come from Settings → General.", "Note", wrap=True), 1)
    settings_row.addWidget(q.button("Edit in Settings", "ghost", on_click=dialog.reject))
    p3.addLayout(settings_row)
    p3.addStretch()
    dialog.add_step("Confirm", page3, "Confirm", "The account that uploads, and what this run sends.", "check")

    def total() -> int:
        return totals[files.index()]

    def update() -> None:
        which = ("new files", "saved files")[files.index()]
        n = count.value()
        seconds = spread.seconds() if spread_on.isChecked() else 0
        spread.setVisible(spread_on.isChecked())
        spread_note.setText("in total, one at a time" if spread_on.isChecked()
                            else "Off: all files start right away")
        verb = ("upload to the server", "are read back and checked")[action.index()]
        if seconds:
            pace = f", one at a time in random order, spread over <b>{rough_duration(seconds)}</b>"
        else:
            pace = f", {workers_spin.value()} at a time"
        text = f"<b>{n:,}</b> of your <b>{total():,}</b> {which} {verb}{pace}."
        need = n * SECONDS_PER_FILE
        if seconds and seconds < need:
            text += (f"<br><span style='color:{TOKENS['warn']}'>Each upload takes about "
                     f"{SECONDS_PER_FILE} s, so {n:,} take at least {rough_duration(need)}.</span>")
        summary.setText(text)
        run_time = max(seconds, need) if seconds else -(-n // workers_spin.value()) * SECONDS_PER_FILE
        takes.setText(f"≈ {rough_duration(run_time)}")
        size_value.setText(f"≈ {n * 2.4 / 1000:.1f} GB")
        picked = files.buttons[files.index()].text().split(" ·")[0]
        dialog.set_crumb(f"{picked} → {action.buttons[action.index()].text()}")

    def on_files(_i: int) -> None:
        count.noun = ("new files", "saved files")[files.index()]
        count.set_total(total(), min(count.value(), total()))
        update()

    files.changed.connect(on_files)
    for signal in (action.changed, count.changed, spread_on.toggled, spread.changed, workers_spin.valueChanged):
        signal.connect(lambda *_: update())
    dialog.check = lambda step: ("Paste the access key to start." if step == 2 and not key.text().strip()
                                 else "")
    update()
    return dialog


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------
class DemoWindow(q.QuietWindow):
    def __init__(self):
        super().__init__("Uploader")
        self.run_page = RunPage(self)
        self.settings_page = SettingsPage()
        self.run_index = self.add_page("Run", "play", self.run_page)
        self.add_page("History", "list", q.Page("History", "Earlier runs show here."))
        self.settings_index = self.add_page("Settings", "sliders", self.settings_page, bottom=True)
        self.set_footnote("Uploader v1.0 · settings.ini", tooltip=f"Qt binding: {QT_API}")
        self.note.action_clicked.connect(lambda: self.run_page.tabs.set_index(1))


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------
def take_shots(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    app = q.make_app([sys.argv[0]])

    def settle() -> None:
        for _ in range(6):
            app.processEvents()

    def save(pixmap, name: str) -> None:
        path = folder / name
        pixmap.save(str(path), "PNG")
        print(f"saved {path}")

    win = DemoWindow()
    win.setAttribute(Qt.WA_DontShowOnScreen, True)
    win.show()
    settle()

    win.set_page(win.settings_index)
    win.settings_page.workers.setValue(6)  # an edit, so the header shows "Unsaved changes"
    settle()
    save(win.grab(), "window-settings.png")

    win.set_page(win.run_index)
    win.run_page.start()
    settle()
    save(win.grab(), "window-run.png")

    win.run_page.show_error()
    settle()
    note = win.note
    top_left = note.mapTo(win, q.QPoint(0, 0))
    area = q.QRect(top_left, note.size()).adjusted(-60, -60, 30 + win.MARGIN, 30 + win.MARGIN)
    save(win.grab(area.intersected(win.rect())), "error-note.png")
    win.note.hide()

    dialog = make_start_dialog(win)
    dialog.setAttribute(Qt.WA_DontShowOnScreen, True)
    dialog.show()
    dialog.adjustSize()
    settle()
    save(dialog.grab(), "step-dialog.png")
    dialog.go(+1)
    dialog.next_btn.setFocus()
    settle()
    save(dialog.grab(), "step-dialog-details.png")
    dialog.reject()
    win.run_page.timer.stop()
    win.close()


def main() -> int:
    if OPTIONS.shots:
        take_shots(Path(OPTIONS.shots))
        return 0
    app = q.make_app()
    win = DemoWindow()
    win.show()
    return q.run_app(app)


if __name__ == "__main__":
    sys.exit(main())
