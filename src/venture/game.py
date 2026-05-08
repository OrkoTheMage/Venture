from __future__ import annotations

import datetime
import random
import shutil
import shlex
import textwrap

from .window import Window
from .renderer import get_ascii_lines
from .state import load_state, save_state
from . import combat, roster as roster_mod, quest as quest_mod, journal as journal_mod
from . import modes

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
            bw = max(10, min(30, self.win.width - 30))
            bar = "[" + "#" * int(bw * pct / 100) + "-" * (bw - int(bw * pct / 100)) + "]"
            qname = self.state.get("quest_name")
            if qname:
                try:
                    danger = int(self.state.get("quest_danger", 0))
                    length = self.state.get("quest_length", "")
                    status += ["", f"\033[1m{qname}\033[0m (Danger: {danger} | Length: {length})"]
                    status.append("")
                    lore = quest_mod.QUEST_LORE.get(qname)
                    if lore:
                        for line in textwrap.wrap(lore, width=max(20, self.win.width - 6))[:3]:
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
                    if name in summary["fallen"]:
                        lines.append(f"   {name}: Lost {hp_pct}% HP and has fallen")
                    elif leveled_to is not None:
                        lines.append(
                            f"   {name}: Lost {hp_pct}% HP and gained {exp} EXP."
                            f" Leveling up to LVL {leveled_to}"
                        )
                    else:
                        lines.append(f"   {name}: Lost {hp_pct}% HP and gained {exp} EXP")
            if summary["rewards"]:
                lines.append("")
                lines.append("Rewards:")
                for r in summary["rewards"]:
                    lines.append(f"   {r}")
            status += lines
        return status

    def _make_greeting(self) -> tuple[str | None, str | None]:
        if not self.player_name:
            return None, None
        greetings = ["Greetings", "Hello", "Well met", "Hail"]
        weathers  = ["sunny", "rainy", "stormy", "foggy", "windy", "snowy", "overcast"]
        events    = [
            "A hawk circles overhead.",
            "A distant horn sounds.",
            "A sudden breeze chills you.",
            "A merchant wagon creaks by.",
            "A stray dog barks in the lane.",
            "The scent of smoke drifts from the east.",
            "Villagers whisper of a strange light.",
        ]
        day_seed = int(datetime.date.today().strftime("%Y%m%d"))
        rng = random.Random(day_seed)
        greeting = (
            f"Hello, {self.player_name}" if not self.estate_name
            else f"{rng.choice(greetings)}, {self.player_name} it's a "
                 f"{rng.choice(weathers)} day in {self.estate_name}"
        )
        return greeting, rng.choice(events)

    def _render_home(self, force_roster_hint: bool = False) -> None:
        status_lines = self._build_status_lines()
        gold = int(self.state.get("gold", 0))
        week = int(self.state.get("week", 0))
        stats_line = f"Coffers: {gold}G  |  Week: {week}"
        stats_extra = 3 if (self.player_name and self.estate_name) else 0
        greeting_lines = 2 if self.player_name else 0
        _hints: list[str] = []
        if force_roster_hint or (self.player_name and not self.roster_seen):
            _hints.append('Type "roster" to view your roster.')
        if self.player_name and self.state.get("gather_allies_done") and not self.state.get("recruit_hint_seen"):
            _hints.append('Type "recruit" to see a list of recruitable party members')
        _has_lvl2_wiz = any(
            h.get("class") == "Wizard" and int(h.get("lvl", 1)) >= 2
            for h in self.state.get("roster", [])
        )
        if self.player_name and _has_lvl2_wiz and not self.state.get("spells_hint_seen"):
            _hints.append('Type "spells" to see a list of castable spells')
        if self.player_name and self.state.get("graveyard") and not self.state.get("graveyard_hint_seen"):
            _hints.append('Type "graveyard" to see a list of fallen heros')
        try:
            j_entries = journal_mod.get_journal_entries(self.state)
            if self.player_name and any(e.get("done") for e in j_entries) and not self.state.get("journal_hint_seen"):
                _hints.append('Type "journal" to see a list of goals for the estate.')
        except Exception:
            pass
        hint_lines = len(_hints) * 2
        avail_h = max(
            0,
            self.win.height - 1 - stats_extra - greeting_lines - hint_lines - len(status_lines),
        )
        display = [ln[:self.win.width] for ln in self.ascii_lines][:avail_h]
        logo_width = max((len(ln.rstrip()) for ln in display), default=0)
        if logo_width > len(stats_line):
            stats_line = stats_line.center(logo_width)
        stats_line = f"\033[1m{stats_line}\033[0m"
        rl: list[str] = display + [""]
        if self.player_name and self.estate_name:
            rl.append(stats_line)
            rl += ["", ""]
        gre, evt = self._make_greeting()
        if gre:
            rl.append(gre)
        if evt:
            rl.append(evt)
        for _hint in _hints:
            rl += ["", _hint]
        rl += [""] + status_lines
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

        self._render_home()

        if not self.player_name:
            print(
                "Welcome, to the world of Venture\n"
                "You are the heir to a great legacy.\n"
                "Your once great house has fallen to the horrors from the depths.\n"
                "Gather great heroes, and cunning allies. Delve the halls of your "
                "ancestors and...\nClaim your birthright!"
            )
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
                lines = quest_mod.build_graveyard_lines(self.state)
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
                lines = journal_mod.build_journal_lines(self.state)
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
