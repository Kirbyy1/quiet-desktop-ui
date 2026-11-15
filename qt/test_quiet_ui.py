"""Behaviour tests for quiet_ui.py. Runs headless:

    python -m unittest test_quiet_ui           (QUIET_QT=pyqt5 or pyside6 to pick the binding)
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import quiet_ui as q  # noqa: E402

APP = q.make_app([sys.argv[0]])


def settle() -> None:
    for _ in range(3):
        APP.processEvents()


class HelperTests(unittest.TestCase):
    def test_rough_duration(self):
        self.assertEqual(q.rough_duration(45), "45 s")
        self.assertEqual(q.rough_duration(12 * 60), "12 min")
        self.assertEqual(q.rough_duration(6360), "1 h 46 min")
        self.assertEqual(q.rough_duration(3600), "1 h")
        self.assertEqual(q.rough_duration(2 * 86400 + 3 * 3600), "2 days 3 h")
        self.assertEqual(q.rough_duration(86400), "1 day")

    def test_short_id(self):
        self.assertEqual(q.short_id("Ab12c9e0f4d7a35b88xY9z"), "Ab12…xY9z")
        self.assertEqual(q.short_id("short"), "short")

    def test_stylesheet_has_no_placeholders(self):
        css = q.stylesheet()
        self.assertNotIn("$", css)
        self.assertIn(q.TOKENS["accent"], css)
        self.assertTrue(Path(q._stylesheet_assets()["check"]).exists())


class InputTests(unittest.TestCase):
    def test_duration_picks_the_largest_whole_unit(self):
        d = q.DurationInput(1800)
        self.assertEqual((d.spin.value(), d.unit.currentText()), (30, "minutes"))
        d.set_seconds(7200)
        self.assertEqual((d.spin.value(), d.unit.currentText()), (2, "hours"))
        d.set_seconds(90)
        self.assertEqual((d.spin.value(), d.unit.currentText()), (90, "seconds"))
        self.assertEqual(d.seconds(), 90)

    def test_count_of(self):
        c = q.CountOf(1000, "files", 500)
        self.assertEqual(c.value(), 500)
        self.assertEqual(c.of.text(), "of 1,000 files")
        c.set_total(0)
        self.assertFalse(c.spin.isEnabled())
        self.assertEqual(c.value(), 0)

    def test_range_keeps_low_below_high(self):
        r = q.RangeInput(30, 120)
        r.low.setValue(200)
        self.assertEqual(r.values(), (200, 200))
        r.high.setValue(10)
        self.assertEqual(r.values(), (10, 10))

    def test_no_wheel_inputs_ignore_the_wheel_without_focus(self):
        spin = q.NoWheelSpinBox(0, 10, 5)
        self.assertEqual(spin.focusPolicy(), q.Qt.StrongFocus)


class SaveStateTests(unittest.TestCase):
    def test_states_and_save_button(self):
        save = q.button("Save changes", "primary")
        state = q.SaveState(save)
        self.assertFalse(state.isVisibleTo(state.parentWidget() or state) and state.text())
        self.assertFalse(save.isEnabled())
        state.set_dirty(True)
        self.assertEqual(state.text(), "Unsaved changes")
        self.assertTrue(save.isEnabled())
        state.set_issues([("name", "Name is empty"), "Port is not a number"])
        self.assertEqual(state.text(), "2 issues to review")
        self.assertIn("Name is empty", state.toolTip())
        seen = []
        state.issue_clicked.connect(seen.append)
        state.click()
        self.assertEqual(seen, [("name", "Name is empty")])
        state.set_issues([])
        state.flash_saved(ms=10_000)
        self.assertEqual(state.text(), "All changes saved")
        self.assertFalse(save.isEnabled())


class StepDialogTests(unittest.TestCase):
    def make(self):
        dlg = q.StepDialog("Start run", finish_text="Start run")
        options = q.OptionList([("Upload", "Send the files"), ("Check", "Read them back")])
        page1 = q.QWidget()
        lay = q.QVBoxLayout(page1)
        lay.addWidget(options)
        dlg.add_step("What to do", page1, "Start a run", "What should this run do?", "play")
        dlg.add_step("Details", q.QWidget(), "Details")
        dlg.add_step("Confirm", q.QWidget(), "Confirm")
        return dlg, options

    def test_steps_back_jumps_and_finish(self):
        dlg, _options = self.make()
        self.assertEqual(dlg.step_label.text(), "Step 1 of 3")
        self.assertFalse(dlg.back_btn.isVisibleTo(dlg))
        self.assertEqual(dlg.next_btn.text(), "Next")
        dlg.jump(2)  # forward jumps are not allowed
        self.assertEqual(dlg.step, 0)
        dlg.go(+1)
        dlg.go(+1)
        self.assertEqual(dlg.step_label.text(), "Step 3 of 3")
        self.assertEqual(dlg.next_btn.text(), "Start run")
        dlg.jump(0)
        self.assertEqual(dlg.step, 0)
        dlg.set_step_visible(1, False)
        dlg.go(+1)
        self.assertEqual((dlg.step, dlg.step_label.text()), (2, "Step 2 of 2"))
        dlg.go(+1)
        self.assertEqual(dlg.result(), q.QDialog.Accepted)

    def test_check_blocks_next_with_a_message(self):
        dlg, _options = self.make()
        dlg.check = lambda step: "Pick a file first." if step == 0 else ""
        dlg.go(+1)
        self.assertEqual(dlg.step, 0)
        self.assertEqual(dlg.message.text(), "Pick a file first.")
        self.assertEqual(dlg.message.property("state"), "bad")

    def test_number_keys_pick_options(self):
        dlg, options = self.make()
        dlg.show()
        settle()
        event = q.QtGui.QKeyEvent(q.QEvent.KeyPress, q._iv(q.Qt.Key_2), q.Qt.NoModifier, "2")
        dlg.keyPressEvent(event)
        self.assertEqual(options.index(), 1)
        self.assertTrue(options.rows[1].check.isVisibleTo(options.rows[1]))
        dlg.reject()


class RunWidgetTests(unittest.TestCase):
    def test_item_row_states(self):
        steps = ["Read", "Check", "Upload"]
        row = q.ItemRow("notes.md", "e8f1…150e · 18 KB")
        row.set_progress(steps, 1, "running")
        self.assertEqual(row.status.text(), "Check…")
        row.set_progress(steps, 1, "failed", result="File changed while it was read")
        self.assertEqual((row.status.text(), row.status.property("state")), ("Failed at Check", "bad"))
        self.assertEqual(row.result.property("state"), "bad")
        row.set_progress(steps, 2, "done")
        self.assertEqual((row.status.text(), row.result.text()), ("Done", "Done"))
        self.assertEqual(row.track.state, "done")

    def test_long_results_are_shortened_with_a_tooltip(self):
        row = q.ItemRow("a")
        long_text = "x" * 400
        row.set_progress(["Go"], 0, "failed", result=long_text)
        self.assertTrue(row.result.text().endswith("…"))
        self.assertEqual(row.result.toolTip(), long_text)

    def test_item_list_newest_on_top_and_empty_state(self):
        items = q.ItemList("Nothing yet.")
        first, second = q.ItemRow("first"), q.ItemRow("second")
        items.add(first)
        items.add(second)
        lay = items.widget().layout()
        self.assertIs(lay.itemAt(1).widget(), second)
        self.assertFalse(items._empty.isVisibleTo(items))
        items.clear()
        self.assertEqual(items.rows, [])
        self.assertTrue(items._empty.isVisibleTo(items))

    def test_segmented_and_switch(self):
        seg = q.Segmented(["A", "B", "C"])
        seen = []
        seg.changed.connect(seen.append)
        seg.set_index(2)
        self.assertEqual((seg.index(), seen), (2, [2]))
        switch = q.ToggleSwitch(True)
        self.assertTrue(switch.isChecked())
        switch.setChecked(False)
        self.assertFalse(switch.isChecked())

    def test_button_kind_switch(self):
        btn = q.button("Start run", "primary", "play")
        self.assertEqual(btn.objectName(), "PrimaryButton")
        q.set_button_kind(btn, "danger", "stop")
        self.assertEqual(btn.objectName(), "DangerButton")


class WindowTests(unittest.TestCase):
    def test_pages_status_and_error_note(self):
        win = q.QuietWindow("Test")
        run = win.add_page("Run", "play", q.Page("Run"))
        settings = win.add_page("Settings", "sliders", q.Page("Settings"), bottom=True)
        win.set_page(settings)
        self.assertTrue(win.nav_buttons[settings].isChecked())
        self.assertFalse(win.nav_buttons[run].isChecked())
        win.set_status("Running", "good")
        self.assertEqual(win._status_text.text(), "Running")
        win.show()
        settle()
        win.show_error("Upload failed", "A long message " * 12)
        settle()
        note = win.note
        self.assertTrue(note.isVisible())
        self.assertGreater(note.height(), 60)  # the text wraps instead of being cut to one line
        self.assertLessEqual(note.geometry().right(), win.frame.width() - 30)
        win.close()


if __name__ == "__main__":
    unittest.main()
