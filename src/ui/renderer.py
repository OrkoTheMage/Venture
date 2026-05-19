from __future__ import annotations
import random
import shutil
import signal
import sys
import textwrap
import time
from pathlib import Path
from .screen import Screen
from ..utils.state import load_state, save_state
from ..logic import quest as quest_mod, progress as journal_mod
from ..logic.events import get_active_event
try:
    from importlib.resources import files
except Exception:
    files = None


# ── ASCII art loader ─────────────────────────────────────────────────────── #

def get_ascii_lines(cols: int, rows: int) -> list[str]:
    target    = "asciiLarge.txt" if cols > 82 and rows > 28 else "asciiSmall.txt"
    asset_dir = "ascii"
    for name in [target]:
        lines = None
        try:
            for candidate in [
                Path.cwd() / name,
                Path.cwd() / asset_dir / name,
                Path(__file__).resolve().parent / name,
                Path(__file__).resolve().parent / asset_dir / name,
                Path(__file__).resolve().parent.parent / asset_dir / name,
            ]:
                if candidate.exists():
                    lines = candidate.read_text().splitlines()
                    break
        except Exception:
            pass
        if lines is None and files is not None and __package__:
            try:
                lines = files(__package__).joinpath(name).read_text().splitlines()
            except Exception:
                try:
                    lines = files(__package__).joinpath(asset_dir).joinpath(name).read_text().splitlines()
                except Exception:
                    pass
        if lines:
            return lines
    return []


# ── Renderer ─────────────────────────────────────────────────────────────── #

# Owns all display state and every render/resize method.
# Initialising Renderer() measures the terminal, creates the Window,
# loads saved game state, and installs the SIGWINCH handler.
class Renderer:

    def __init__(self) -> None:
        # ── Terminal measurement ─────────────────────────────────────────── #
        term       = shutil.get_terminal_size(fallback=(80, 24))
        self.cols  = term.columns
        self.rows  = term.lines
        self.compact = self.rows < 45 or self.cols < 115

        # ── Window ──────────────────────────────────────────────────────── #
        self.win = Screen(
            width =max(20, min(self.cols - 4, 160)),
            height=max(8,  min(self.rows - 4, 60)),
        )

        # ── Game state ──────────────────────────────────────────────────── #
        self.state:        dict       = load_state()
        self.player_name:  str | None = self.state.get("player_name")
        self.estate_name:  str | None = self.state.get("estate_name")
        self.roster_seen:  bool       = self.state.get("roster_seen", False)
        self.ascii_lines:  list[str]  = get_ascii_lines(self.cols, self.rows)
        self._resize_pending: bool    = False

        # ── Live resize support ──────────────────────────────────────────── #
        try:
            def _on_sigwinch(signum, frame):   # noqa: ARG001
                self._resize_pending = True
            signal.signal(signal.SIGWINCH, _on_sigwinch)
        except (AttributeError, OSError):
            pass

        self.win.resize_check = lambda: self._resize_pending
        self.win.on_resize    = self.home_on_resize

    # ── Resize ───────────────────────────────────────────────────────────── #

    # Re-measure terminal; update window dimensions, compact flag, and ASCII.
    def apply_resize(self) -> None:
        term         = shutil.get_terminal_size(fallback=(80, 24))
        self.cols    = term.columns
        self.rows    = term.lines
        self.compact = self.rows < 45 or self.cols < 115
        if self.win is not None:
            self.win.width  = max(20, min(self.cols - 4, 160))
            self.win.height = max(8,  min(self.rows - 4, 60))
        self.ascii_lines    = get_ascii_lines(self.cols, self.rows)
        self._resize_pending = False

    # Resize callback active while the home-screen prompt is showing.
    def home_on_resize(self) -> None:
        self.apply_resize()
        self.render_home()

    # ── Status lines ─────────────────────────────────────────────────────── #

    def _build_status_lines(self) -> list[str]:
        qi     = quest_mod.quest_info()
        status: list[str] = []

        if qi.get("running"):
            rem     = qi["remaining"]
            rem_str = quest_mod.format_duration(rem)
            pct     = int(min(100, qi["elapsed"] / qi["duration"] * 100))
            qname   = self.state.get("quest_name")
            if qname:
                if self.compact:
                    bw  = max(8, min(16, self.win.width - 50))
                    bar = "▕" + "\033[32m" + "█" * int(bw * pct / 100) + "\033[0m" + "░" * (bw - int(bw * pct / 100)) + "▏"
                    try:
                        danger   = int(self.state.get("quest_danger", 0))
                        length   = self.state.get("quest_length", "")
                        location = self.state.get("quest_location", "")
                        loc_str  = f" | {location}" if location else ""
                        status  += [
                            "",
                            f"\033[1mQUEST: {qname}\033[0m  (D:{danger} | {length}{loc_str})",
                            "",
                        ]
                        lore = quest_mod.QUEST_LORE.get(qname)
                        if lore:
                            for line in quest_mod.render_lore(lore, width=max(20, self.win.width - 6), indent=""):
                                status.append(f"  {line}")
                        status += [
                            "",
                            f"\033[1mQuest Progress:\033[0m {bar} {pct}% ({rem_str})",
                            "Press ENTER to refresh.",
                        ]
                    except Exception:
                        status += ["", f"{qname}  {bar} {pct}% ({rem_str})", "Press ENTER to refresh."]
                else:
                    bw  = max(10, min(30, self.win.width - 30))
                    bar = "▕" + "\033[32m" + "█" * int(bw * pct / 100) + "\033[0m" + "░" * (bw - int(bw * pct / 100)) + "▏"
                    try:
                        danger   = int(self.state.get("quest_danger", 0))
                        length   = self.state.get("quest_length", "")
                        location = self.state.get("quest_location", "")
                        loc_str  = f" | {location}" if location else ""
                        status  += ["", f"\033[1mQUEST: {qname}\033[0m (Danger: {danger} | Length: {length}{loc_str})"]
                        status.append("")
                        lore = quest_mod.QUEST_LORE.get(qname)
                        if lore:
                            for line in quest_mod.render_lore(lore, width=max(20, self.win.width - 6), indent=""):
                                status.append(f"  {line}")
                    except Exception:
                        pass
                    status += [
                        "",
                        f"\033[1mQuest Progress:\033[0m {bar} {pct}% ({rem_str})",
                        "Leave and come back to see progress or press 'ENTER' to refresh.",
                    ]

        elif qi.get("completed"):
            summary          = quest_mod.apply_quest_damage()
            self.state       = load_state()
            self.roster_seen = self.state.get("roster_seen", False)
            lines = ["", "Quest Complete!"]
            if summary["damage_taken"]:
                lines.append("Results:")
                for name, hp_pct, exp, leveled_to in summary["damage_taken"]:
                    hp_colour = "\033[32m" if hp_pct == 0 else "\033[31m"
                    if name in summary["fallen"]:
                        lines.append(f"   {name}: Lost {hp_colour}{hp_pct}% HP\033[0m and has fallen")
                    elif leveled_to is not None:
                        lines.append(
                            f"   {name}: Lost {hp_colour}{hp_pct}% HP\033[0m and gained \033[36m{exp} EXP\033[0m."
                            f" Leveling up to LVL {leveled_to}"
                        )
                    else:
                        lines.append(f"   {name}: Lost {hp_colour}{hp_pct}% HP\033[0m and gained \033[36m{exp} EXP\033[0m")
            if summary["rewards"]:
                lines.append("")
                lines.append("Rewards:")
                for r in summary["rewards"]:
                    lines.append(f"   {r}")
            status += lines

        return status

    # ── Greeting / event ─────────────────────────────────────────────────── #

    def _make_greeting(self) -> tuple[str | None, str | None, str | None]:
        if not self.player_name:
            return None, None, None
        greetings = ["Greetings", "Hello", "Well met", "Hail"]
        weathers  = ["sunny", "rainy", "stormy", "foggy", "windy", "snowy", "overcast"]
        rng       = random.Random(int(self.state.get("week", 0)))
        greeting  = (
            f"Hello, {self.player_name}" if not self.estate_name
            else f"{rng.choice(greetings)}, {self.player_name} it's a "
                 f"{rng.choice(weathers)} day in {self.estate_name}"
        )
        if self.state.get("gather_allies_done"):
            week  = int(self.state.get("week", 0))
            event = get_active_event(week, self.state)
            return greeting, event["name"], event["lore"]
        return greeting, None, None

    # ── Rare-event handlers ───────────────────────────────────────────────── #

    def handle_pending_rare_event(self) -> None:
        event = self.state.get("pending_rare_event")
        if event == "styx":
            self._handle_styx_revival()
        elif event == "ritual":
            self._handle_dark_ritual()
        self.state.pop("pending_rare_event", None)
        save_state(self.state)

    def _handle_styx_revival(self) -> None:
        graveyard = self.state.get("graveyard", [])
        if not graveyard:
            print("[Returned From The Styx] No fallen heroes to revive.")
            return
        print("\n[Returned From The Styx] Choose a hero to revive:")
        for i, e in enumerate(graveyard, 1):
            print(f"  {i}. {e['name']} the {e['class']} (Lvl {e['lvl']}) — fell during '{e['quest']}'")
        try:
            choice = self.win.prompt("Choose a number (or ENTER to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(graveyard)):
            print("Skipped.")
            return
        idx   = int(choice) - 1
        entry = graveyard[idx]
        from .combat import max_hp_for
        _EXP_FOR_LEVEL = {1: 0, 2: 100, 3: 200, 4: 400, 5: 800}
        lvl    = int(entry.get("lvl", 1))
        max_hp = float(max_hp_for(entry["class"], lvl))
        hero   = {
            "name":   entry["name"],
            "class":  entry["class"],
            "lvl":    lvl,
            "hp":     max_hp * 0.5,
            "max_hp": max_hp,
            "exp":    _EXP_FOR_LEVEL.get(lvl, 0),
        }
        self.state.setdefault("roster", []).append(hero)
        graveyard.pop(idx)
        self.state["graveyard"] = graveyard
        save_state(self.state)
        print(f"{hero['name']} the {hero['class']} has returned from the Styx.")

    def _handle_dark_ritual(self) -> None:
        roster   = self.state.get("roster", [])
        eligible = [h for h in roster if int(h.get("lvl", 1)) < 5]
        if not eligible:
            print("[Dark Ritual] No heroes eligible for levelling (all at max level).")
            return
        print("\n[Dark Ritual] Choose a hero to gain 1 level:")
        for i, h in enumerate(eligible, 1):
            print(f"  {i}. {h['name']} the {h['class']} (Lvl {h['lvl']})")
        try:
            choice = self.win.prompt("Choose a number (or ENTER to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not choice.isdigit() or not (1 <= int(choice) <= len(eligible)):
            print("Skipped.")
            return
        target          = eligible[int(choice) - 1]
        _EXP_THRESHOLDS = [100, 200, 400, 800]
        cur_lvl         = int(target.get("lvl", 1))
        if cur_lvl < 5:
            needed_exp = _EXP_THRESHOLDS[cur_lvl - 1]
            gap        = max(0, needed_exp - int(target.get("exp", 0)))
            quest_mod._award_exp(target, gap)
            save_state(self.state)
            print(f"{target['name']} advances to Lvl {target['lvl']}.")

    # ── Logo animation ────────────────────────────────────────────────────── #

    # Startup animation.
    # first_launch=True  — typewriter intro then title reveal + fade.
    # first_launch=False — left-to-right logo wipe then title reveal + fade.
    def animate_logo(self, first_launch: bool = False) -> None:
        lines     = [ln[: self.win.width] for ln in self.ascii_lines[: self.win.height]]
        max_width = max((len(ln) for ln in lines), default=0) if lines else 0

        title      = "Claim your birthright!"
        left_pad   = max(0, (max_width - len(title)) // 2)
        prefix     = " " * left_pad
        full_title = prefix + title

        if first_launch:
            intro = [
                "Welcome, to the world of Venture",
                "You are the heir to a great legacy.",
                "Your once great house has fallen to the horrors from the depths.",
                "Gather great heroes, and cunning allies. Delve the halls of your ancestors and...",
            ]
            print("\033[H\033[J", end="", flush=True)
            print()
            for line in intro:
                for ch in line:
                    print(ch, end="")
                    sys.stdout.flush()
                    time.sleep(0.015)
                print()
                time.sleep(0.25)
            lines_above = 1 + len(intro) + 1
        else:
            if lines and max_width:
                print("\033[H\033[J", end="", flush=True)
                for _ in lines:
                    print()
                col = 0
                while True:
                    col = min(col + 2, max_width)
                    print(f"\033[{len(lines)}A", end="")
                    for ln in lines:
                        print(f"\r{ln[:col]}")
                    sys.stdout.flush()
                    time.sleep(0.01)
                    if col >= max_width:
                        break
            lines_above = 1

        # ── Title reveal ─────────────────────────────────────────────────── #
        print()
        print(f"\r{prefix}", end="")
        for ch in title:
            print(f"\033[1m{ch}\033[0m", end="")
            sys.stdout.flush()
            time.sleep(0.05)
        time.sleep(0.8)

        # ── Fade out ──────────────────────────────────────────────────────── #
        print(f"\033[{lines_above}A\r", end="")
        if first_launch:
            print()
            for line in intro:
                print(f"\033[2m{line}\033[0m")
        print()
        print(f"\r\033[2m{full_title}\033[0m", end="")
        sys.stdout.flush()
        time.sleep(0.3)

    # ── Home screen ───────────────────────────────────────────────────────── #

    def render_home(self, force_roster_hint: bool = False) -> None:
        status_lines = self._build_status_lines()
        gold         = int(self.state.get("gold", 0))
        week         = int(self.state.get("week", 0))
        stats_line   = f"Coffers: {gold}G  |  Week: {week}"
        has_identity = bool(self.player_name and self.estate_name)
        has_player   = bool(self.player_name)

        _hints: list[str] = []
        if force_roster_hint or (has_player and not self.roster_seen):
            _hints.append('Type "roster" to view your roster.')
        if has_player and self.state.get("gather_allies_done") and not self.state.get("recruit_hint_seen"):
            _hints.append('Type "recruit" to see a list of recruitable party members')
        if has_player and not self.state.get("spells_hint_seen") and any(
            h.get("class") == "Wizard" and int(h.get("lvl", 1)) >= 2
            for h in self.state.get("roster", [])
        ):
            _hints.append('Type "spells" to see a list of castable spells')
        if has_player and self.state.get("graveyard") and not self.state.get("graveyard_hint_seen"):
            _hints.append('Type "graveyard" to see a list of fallen heros')
        try:
            j_entries = journal_mod.get_journal_entries(self.state)
            if has_player and any(e.get("done") for e in j_entries) and not self.state.get("journal_hint_seen"):
                _hints.append('Type "journal" to see a list of goals for the estate.')
        except Exception:
            pass

        gre, evt_name, evt_lore = self._make_greeting()
        lore_lines: list[str] = (
            [f"  {ln}" for ln in textwrap.wrap(evt_lore, width=max(20, self.win.width - 4))]
            if evt_lore else []
        )

        if self.compact:
            c_static = (
                (1 if has_identity else 0)
                + (1 if has_identity else 0)
                + (1 if has_player else 0)
                + (1 if has_player and evt_name else 0)
                + (1 + 1 + len(lore_lines) if has_player and evt_name else 0)
                + (2 if _hints else 0)
                + len(status_lines)
            )
            avail_h    = max(0, self.win.height - 1 - c_static)
            display    = [ln[:self.win.width] for ln in self.ascii_lines][:avail_h]
            logo_width = max((len(ln.rstrip()) for ln in display), default=0)
            sl  = stats_line.center(logo_width) if logo_width > len(stats_line) else stats_line
            rl: list[str] = list(display)
            if has_identity:
                rl.append(f"\033[1m{sl}\033[0m")
            rl.append("")
            if gre:
                rl.append(gre)
            if evt_name:
                rl += ["", f"\033[1mEVENT: {evt_name}\033[0m", ""]
                rl.extend(lore_lines)
            for hint in _hints[:1]:
                rl += ["", hint]
            rl += status_lines
        else:
            r_static = (
                1
                + (3 if has_identity else 0)
                + (1 if has_player else 0)
                + (1 if has_player and evt_name else 0)
                + (1 + 1 + len(lore_lines) if has_player and evt_name else 0)
                + len(_hints) * 2
                + len(status_lines)
            )
            avail_h    = max(0, self.win.height - 1 - r_static)
            display    = [ln[:self.win.width] for ln in self.ascii_lines][:avail_h]
            logo_width = max((len(ln.rstrip()) for ln in display), default=0)
            sl  = stats_line.center(logo_width) if logo_width > len(stats_line) else stats_line
            rl  = display + [""]
            if has_identity:
                rl.append(f"\033[1m{sl}\033[0m")
                rl += ["", ""]
            if gre:
                rl.append(gre)
            if evt_name:
                rl += ["", f"\033[1mEVENT: {evt_name}\033[0m", ""]
                rl.extend(lore_lines)
            for hint in _hints:
                rl += ["", hint]
            rl += status_lines

        self.win.render(rl[:self.win.height])
