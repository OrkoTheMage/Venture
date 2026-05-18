from __future__ import annotations

import random
import shutil
import shlex
import sys
import textwrap
import time

from .window import Window
from .renderer import get_ascii_lines
from .state import load_state, save_state
from . import combat, roster as roster_mod, quest as quest_mod, journal as journal_mod
from . import modes
from .events import get_active_event

try:
    from . import dev as dev_mod
except ImportError:
    dev_mod = None


class Game:

    def __init__(self) -> None:
        self.win: Window | None = None
        self.state: dict = {}
        self.compact: bool = False
        self.player_name: str | None = None
        self.estate_name: str | None = None
        self.roster_seen: bool = False
        self.ascii_lines: list[str] = []

    # ── Home screen helpers ──────────────────────────────────────────────── #

    def _build_status_lines(self) -> list[str]:
        qi = quest_mod.quest_info()
        status: list[str] = []
        if qi.get("running"):
            rem = qi["remaining"]
            rem_str = quest_mod.format_duration(rem)
            pct = int(min(100, qi["elapsed"] / qi["duration"] * 100))
            qname = self.state.get("quest_name")
            if qname:
                if self.compact:
                    bw = max(8, min(16, self.win.width - 50))
                    bar = "[" + "#" * int(bw * pct / 100) + "-" * (bw - int(bw * pct / 100)) + "]"
                    try:
                        danger = int(self.state.get("quest_danger", 0))
                        length = self.state.get("quest_length", "")
                        location = self.state.get("quest_location", "")
                        loc_str = f" | {location}" if location else ""
                        status += [
                            "",
                            f"\033[1mQUEST: {qname}\033[0m  (D:{danger} | {length}{loc_str})",
                            "",
                        ]
                        lore = quest_mod.QUEST_LORE.get(qname)
                        if lore:
                            for line in textwrap.wrap(lore, width=max(20, self.win.width - 6)):
                                status.append(f"  {line}")
                        status += [
                            "",
                            f"\033[1mQuest Progress:\033[0m {bar} {pct}% ({rem_str})",
                            "Press ENTER to refresh.",
                        ]
                    except Exception:
                        status += ["", f"{qname}  {bar} {pct}% ({rem_str})", "Press ENTER to refresh."]
                else:
                    bw = max(10, min(30, self.win.width - 30))
                    bar = "[" + "#" * int(bw * pct / 100) + "-" * (bw - int(bw * pct / 100)) + "]"
                    try:
                        danger = int(self.state.get("quest_danger", 0))
                        length = self.state.get("quest_length", "")
                        location = self.state.get("quest_location", "")
                        loc_str = f" | {location}" if location else ""
                        status += ["", f"\033[1mQUEST: {qname}\033[0m (Danger: {danger} | Length: {length}{loc_str})"]
                        status.append("")
                        lore = quest_mod.QUEST_LORE.get(qname)
                        if lore:
                            for line in textwrap.wrap(lore, width=max(20, self.win.width - 6)):
                                status.append(f"  {line}")
                    except Exception:
                        pass
                    status += [
                        "",
                        f"\033[1mQuest Progress:\033[0m {bar} {pct}% ({rem_str})",
                        "Leave and come back to see progress or press 'ENTER' to refresh.",
                    ]
        elif qi.get("completed"):
            summary = quest_mod.apply_quest_damage()
            self.state = load_state()
            self.roster_seen = self.state.get("roster_seen")
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

    def _make_greeting(self) -> tuple[str | None, str | None, str | None]:
        if not self.player_name:
            return None, None, None
        greetings = ["Greetings", "Hello", "Well met", "Hail"]
        weathers  = ["sunny", "rainy", "stormy", "foggy", "windy", "snowy", "overcast"]
        day_seed = int(self.state.get("week", 0))
        rng = random.Random(day_seed)
        greeting = (
            f"Hello, {self.player_name}" if not self.estate_name
            else f"{rng.choice(greetings)}, {self.player_name} it's a "
                 f"{rng.choice(weathers)} day in {self.estate_name}"
        )
        # Active weekly event — only shown after Gather Allies is complete
        if self.state.get("gather_allies_done"):
            week = int(self.state.get("week", 0))
            event = get_active_event(week, self.state)
            return greeting, event["name"], event["lore"]
        return greeting, None, None

    def _handle_pending_rare_event(self) -> None:
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
        idx = int(choice) - 1
        entry = graveyard[idx]
        from .combat import max_hp_for
        _EXP_FOR_LEVEL = {1: 0, 2: 100, 3: 200, 4: 400, 5: 800}
        lvl = int(entry.get("lvl", 1))
        max_hp = float(max_hp_for(entry["class"], lvl))
        hero = {
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
        roster = self.state.get("roster", [])
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
        target = eligible[int(choice) - 1]
        _EXP_THRESHOLDS = [100, 200, 400, 800]
        cur_lvl = int(target.get("lvl", 1))
        if cur_lvl < 5:
            needed_exp = _EXP_THRESHOLDS[cur_lvl - 1]
            gap = max(0, needed_exp - int(target.get("exp", 0)))
            quest_mod._award_exp(target, gap)
            save_state(self.state)
            print(f"{target['name']} advances to Lvl {target['lvl']}.")

    def _animate_logo(self, first_launch: bool = False) -> None:
        """Startup animation.

        first_launch=True  — typewriter intro copy then title reveal + fade.
        first_launch=False — left-to-right logo wipe then title reveal + fade.
        """
        lines = [ln[: self.win.width] for ln in self.ascii_lines[: self.win.height]]
        max_width = max((len(ln) for ln in lines), default=0) if lines else 0

        title    = "Claim your birthright!"
        left_pad = max(0, (max_width - len(title)) // 2)
        prefix   = " " * left_pad
        full_title = prefix + title

        if first_launch:
            # ── Typewriter intro ─────────────────────────────────────────── #
            intro = [
                "Welcome, to the world of Venture",
                "You are the heir to a great legacy.",
                "Your once great house has fallen to the horrors from the depths.",
                "Gather great heroes, and cunning allies. Delve the halls of your ancestors and...",
            ]
            print("\033[H\033[J", end="", flush=True)
            print()  # top breathing room
            for line in intro:
                for ch in line:
                    print(ch, end="")
                    sys.stdout.flush()
                    time.sleep(0.015)
                print()          # newline after each intro line
                time.sleep(0.25) # brief pause before next line

            # lines_above: blank(1) + intro lines + blank(1) before title
            lines_above = 1 + len(intro) + 1

        else:
            # ── Logo wipe ────────────────────────────────────────────────── #
            if lines and max_width:
                print("\033[H\033[J", end="", flush=True)
                for _ in lines:
                    print()
                step = 2
                col  = 0
                while True:
                    col = min(col + step, max_width)
                    print(f"\033[{len(lines)}A", end="")
                    for ln in lines:
                        print(f"\r{ln[:col]}")
                    sys.stdout.flush()
                    time.sleep(0.01)
                    if col >= max_width:
                        break

            lines_above = 1  # blank before title

        # ── Title reveal (shared) ─────────────────────────────────────────── #
        print()  # blank line before title
        print(f"\r{prefix}", end="")
        for ch in title:
            print(f"\033[1m{ch}\033[0m", end="")
            sys.stdout.flush()
            time.sleep(0.05)

        # ── Hold ──────────────────────────────────────────────────────────── #
        time.sleep(0.8)

        # ── Fade out ──────────────────────────────────────────────────────── #
        # Dim everything that was printed (intro block or just title)
        print(f"\033[{lines_above}A\r", end="")
        if first_launch:
            print()  # blank
            for line in intro:
                print(f"\033[2m{line}\033[0m")
        print()  # blank before title
        print(f"\r\033[2m{full_title}\033[0m", end="")
        sys.stdout.flush()
        time.sleep(0.3)
        # _render_home() will hard-clear the screen from here

    def _render_home(self, force_roster_hint: bool = False) -> None:
        status_lines = self._build_status_lines()
        gold = int(self.state.get("gold", 0))
        week = int(self.state.get("week", 0))
        stats_line = f"Coffers: {gold}G  |  Week: {week}"
        has_identity = bool(self.player_name and self.estate_name)
        has_player = bool(self.player_name)

        _hints: list[str] = []
        if force_roster_hint or (has_player and not self.roster_seen):
            _hints.append('Type "roster" to view your roster.')
        if has_player and self.state.get("gather_allies_done") and not self.state.get("recruit_hint_seen"):
            _hints.append('Type "recruit" to see a list of recruitable party members')
        _has_lvl2_wiz = any(
            h.get("class") == "Wizard" and int(h.get("lvl", 1)) >= 2
            for h in self.state.get("roster", [])
        )
        if has_player and _has_lvl2_wiz and not self.state.get("spells_hint_seen"):
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

        # Pre-wrap lore for both modes so we can account for its line count in static calculations
        lore_lines: list[str] = (
            [f"  {ln}" for ln in textwrap.wrap(evt_lore, width=max(20, self.win.width - 4))]
            if evt_lore else []
        )

        if self.compact:
            # Compact: no blank after ASCII, greeting+event name, lore, at most 1 hint
            # Static lines (non-ASCII): stats? + greeting? + event name + lore + hint+blank? + blank+status
            c_static = (
                (1 if has_identity else 0)
                + (1 if has_identity else 0)  # blank between stats and greeting
                + (1 if has_player else 0)  # greeting
                + (1 if has_player and evt_name else 0)  # blank before event
                + (1 + 1 + len(lore_lines) if has_player and evt_name else 0)  # event name + blank + lore
                + (2 if _hints else 0)  # one hint = blank + hint text
                + len(status_lines)
            )
            avail_h = max(0, self.win.height - 1 - c_static)
            display = [ln[:self.win.width] for ln in self.ascii_lines][:avail_h]
            logo_width = max((len(ln.rstrip()) for ln in display), default=0)
            sl = stats_line.center(logo_width) if logo_width > len(stats_line) else stats_line
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
            # Regular: blank after ASCII, stats + 2 blanks, greeting + event name + lore, all hints
            r_static = (
                1  # blank line after ASCII
                + (3 if has_identity else 0)  # stats + 2 blanks
                + (1 if has_player else 0)    # greeting
                + (1 if has_player and evt_name else 0)  # blank before event
                + (1 + 1 + len(lore_lines) if has_player and evt_name else 0)  # event name + blank + wrapped lore
                + len(_hints) * 2             # blank + hint text per hint
                + len(status_lines)
            )
            avail_h = max(0, self.win.height - 1 - r_static)
            display = [ln[:self.win.width] for ln in self.ascii_lines][:avail_h]
            logo_width = max((len(ln.rstrip()) for ln in display), default=0)
            sl = stats_line.center(logo_width) if logo_width > len(stats_line) else stats_line
            rl = display + [""]
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

    # ── Entry point ─────────────────────────────────────────────────────── #

    def play(self) -> None:
        term = shutil.get_terminal_size(fallback=(80, 24))
        cols, rows = term.columns, term.lines
        self.compact = rows < 45 or cols < 115
        self.win = Window(
            width=max(20, min(cols - 4, 160)),
            height=max(8, min(rows - 4, 60)),
        )
        self.state = load_state()
        self.player_name = self.state.get("player_name")
        self.estate_name = self.state.get("estate_name")
        self.roster_seen = self.state.get("roster_seen")
        self.ascii_lines = get_ascii_lines(cols, rows)

        self._animate_logo(first_launch=not bool(self.player_name))
        self._render_home()

        if not self.player_name:
            try:
                name = self.win.prompt("What is your name? ").strip()
            except (EOFError, KeyboardInterrupt):
                name = ""
            if name:
                try:
                    estate = self.win.prompt("What is the name of your estate? ").strip()
                except (EOFError, KeyboardInterrupt):
                    estate = ""
                if estate:
                    self.state["estate_name"] = estate
                self.state["player_name"] = name
                save_state(self.state)
                self.player_name = name
                self.estate_name = self.state.get("estate_name")
                self._render_home(force_roster_hint=True)

        # ── main command loop ────────────────────────────────────────────── #
        skip_prompt = False
        while True:
            combat.apply_regen(self.state)
            try:
                if skip_prompt:
                    cmd = ""
                    skip_prompt = False
                else:
                    cmd = self.win.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Goodbye!")
                return

            if not self.roster_seen:
                if not cmd:
                    pass
                else:
                    try:
                        _parts = shlex.split(cmd)
                    except ValueError:
                        _parts = cmd.split()
                    verb_check = _parts[0].lower() if _parts else ""
                    if verb_check in ("quit", "exit"):
                        print("Goodbye!")
                        return
                    if verb_check != "roster":
                        print("Please type 'roster' to view your roster before proceeding.")
                        continue
                    if modes.enter_roster_mode(self):
                        return
                    self._render_home()
                    print('\nType "quest" to view available quests.')
                continue

            if not cmd:
                if self.state.get("pending_rare_event"):
                    self._handle_pending_rare_event()
                self._render_home()
                continue

            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()
            verb = parts[0].lower() if parts else ""

            if verb == "quest":
                if quest_mod.quest_info().get("running"):
                    qi2 = quest_mod.quest_info()
                    print(f"Already on a quest — {quest_mod.format_duration(qi2['remaining'])} remaining.")
                    continue
                if self.state.get("gather_allies_done"):
                    _roster_count = len(self.state.get("roster", []))
                    if _roster_count < 4:
                        _hero_word = "hero" if _roster_count == 1 else "heroes"
                        print(
                            f"Your roster only has {_roster_count} {_hero_word} — you need at least 4 to "
                            f"embark on a quest. Type 'recruit' to hire more heroes first."
                        )
                        continue
                if modes.enter_quest_mode(self):
                    return
                self._render_home()

            elif verb == "roster":
                was_first = not self.roster_seen
                if modes.enter_roster_mode(self):
                    return
                self._render_home()
                if was_first:
                    print('\nType "quest" to view available quests.')

            elif verb == "spells":
                self.state["spells_hint_seen"] = True
                save_state(self.state)
                if quest_mod.quest_info().get("running"):
                    print("Cannot cast spells while a quest is in progress.")
                    continue
                if modes.enter_spell_mode(self):
                    return
                self._render_home()

            elif verb == "recruit":
                if not self.state.get("gather_allies_done"):
                    print("Your best chance to gather allies right now is on a quest — look for 'Gather Allies' in the quest list.")
                    continue
                if quest_mod.quest_info().get("running"):
                    print("Cannot recruit while a quest is in progress.")
                    continue
                roster_size = len(self.state.get("roster", []))
                if roster_size >= roster_mod.ROSTER_CAP:
                    print(f"Roster is full ({roster_mod.ROSTER_CAP}/{roster_mod.ROSTER_CAP}). Dismiss a hero in the roster menu first.")
                    continue
                self.state["recruit_hint_seen"] = True
                save_state(self.state)
                if modes.enter_recruit_mode(self):
                    return
                self._render_home()

            elif verb == "dev":
                if dev_mod is None:
                    print("Unknown command. Type 'help'.")
                else:
                    self.state = dev_mod.handle_dev_command(parts, self.state, cols, rows, self.compact)

            elif verb in ("quit", "exit"):
                print("Goodbye!")
                return

            elif verb == "graveyard":
                self.state["graveyard_hint_seen"] = True
                save_state(self.state)
                lines = quest_mod.build_graveyard_lines(self.state, compact=self.compact)
                self.win.render(lines[:self.win.height])
                try:
                    self.win.prompt("graveyard> ", hint="Press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                self._render_home()
                skip_prompt = True

            elif verb == "journal":
                self.state["journal_hint_seen"] = True
                save_state(self.state)
                lines = journal_mod.build_journal_lines(self.state, compact=self.compact)
                self.win.render(lines[:self.win.height])
                try:
                    self.win.prompt("journal> ", hint="Press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                self._render_home()
                skip_prompt = True

            elif verb == "help":
                print("Commands: quest, roster, recruit, spells, graveyard, journal, help, quit")

            else:
                print("Unknown command. Type 'help'.")
