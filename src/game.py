from __future__ import annotations
import shlex
from .ui.renderer import Renderer
from .utils.state import save_state
from .logic import combat, quest as quest_mod
from .logic import heroes as roster_mod
from .ui import modes
try:
    from . import dev as dev_mod
except ImportError:
    dev_mod = None


def play() -> None:
    r = Renderer()
    r.animate_logo(first_launch=not bool(r.player_name))
    r.render_home()
    if r.state.get("pending_rare_event"):
        r.handle_pending_rare_event()
        r.render_home()

    if not r.player_name:
        try:
            name = r.win.prompt("What is your name? ").strip()
        except (EOFError, KeyboardInterrupt):
            name = ""
        if name:
            try:
                estate = r.win.prompt("What is the name of your estate? ").strip()
            except (EOFError, KeyboardInterrupt):
                estate = ""
            if estate:
                r.state["estate_name"] = estate
            r.state["player_name"] = name
            save_state(r.state)
            r.player_name = name
            r.estate_name = r.state.get("estate_name")
            r.render_home(force_roster_hint=True)

    # ── Main command loop ────────────────────────────────────────────────── #
    while True:
        if r._resize_pending:
            r.apply_resize()
            r.render_home()
        r.win.on_resize = r.home_on_resize
        combat.apply_regen(r.state)

        try:
            cmd = r.win.prompt("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("Goodbye!")
            return

        # Force roster first
        if not r.roster_seen:
            if cmd:
                try:
                    _parts = shlex.split(cmd)
                except ValueError:
                    _parts = cmd.split()
                verb_check = _parts[0].lower() if _parts else ""
                if verb_check in ("quit", "exit"):
                    print("Goodbye!")
                    return
                if verb_check != "roster":
                    r.win.pending_hint = "Please type 'roster' to view your roster before proceeding."
                    r.render_home()
                    continue
                if modes.enter_roster_mode(r):
                    return
                r.render_home()
                r.win.pending_hint = 'Type "quest" to view available quests.'
            continue

        if not cmd:
            r.render_home()
            if r.state.get("pending_rare_event"):
                r.handle_pending_rare_event()
                r.render_home()
            continue

        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()
        verb = parts[0].lower() if parts else ""

        if verb == "quest":
            if quest_mod.quest_info().get("running"):
                qi = quest_mod.quest_info()
                r.win.pending_hint = f"Already on a quest — {quest_mod.format_duration(qi['remaining'])} remaining."
                r.render_home()
                continue
            if r.state.get("gather_allies_done"):
                count = len(r.state.get("roster", []))
                if count < 4:
                    word = "hero" if count == 1 else "heroes"
                    r.win.pending_hint = (
                        f"Your roster only has {count} {word} — you need at least 4 to "
                        f"embark on a quest. Type 'recruit' to hire more heroes first."
                    )
                    r.render_home()
                    continue
            if modes.enter_quest_mode(r):
                return
            r.render_home()

        elif verb == "roster":
            was_first = not r.roster_seen
            if modes.enter_roster_mode(r):
                return
            r.render_home()
            if was_first:
                r.win.pending_hint = 'Type "quest" to view available quests.'

        elif verb == "spells":
            r.state["spells_hint_seen"] = True
            save_state(r.state)
            if quest_mod.quest_info().get("running"):
                r.win.pending_hint = "Cannot cast spells while a quest is in progress."
                r.render_home()
                continue
            if modes.enter_spell_mode(r):
                return
            r.render_home()

        elif verb == "recruit":
            if not r.state.get("gather_allies_done"):
                r.win.pending_hint = "Your best chance to gather allies right now is on a quest — look for 'Gather Allies' in the quest list."
                r.render_home()
                continue
            if quest_mod.quest_info().get("running"):
                r.win.pending_hint = "Cannot recruit while a quest is in progress."
                r.render_home()
                continue
            if len(r.state.get("roster", [])) >= roster_mod.ROSTER_CAP:
                r.win.pending_hint = f"Roster is full ({roster_mod.ROSTER_CAP}/{roster_mod.ROSTER_CAP}). Dismiss a hero in the roster menu first."
                r.render_home()
                continue
            r.state["recruit_hint_seen"] = True
            save_state(r.state)
            if modes.enter_recruit_mode(r):
                return
            r.render_home()

        elif verb == "graveyard":
            r.state["graveyard_hint_seen"] = True
            save_state(r.state)
            if modes.enter_graveyard_mode(r):
                return
            r.render_home()

        elif verb == "journal":
            r.state["journal_hint_seen"] = True
            save_state(r.state)
            if modes.enter_journal_mode(r):
                return
            r.render_home()

        elif verb == "dev":
            if dev_mod is None:
                r.win.pending_hint = "Unknown command: Type 'help'."
                r.render_home()
            else:
                r.state = dev_mod.handle_dev_command(parts, r.state, r.cols, r.rows, r.compact)

        elif verb in ("quit", "exit"):
            print("Goodbye!")
            return

        elif verb == "help":
            r.win.pending_hint = "Commands: quest, roster, recruit, spells, graveyard, journal, help, quit"
            r.render_home()

        else:
            r.win.pending_hint = "Unknown command: Type 'help'."
            r.render_home()
