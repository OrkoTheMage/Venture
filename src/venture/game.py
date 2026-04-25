import random
import shutil

from .window import Window
from .renderer import get_ascii_lines
from .state import load_state, save_state
from . import combat, roster as roster_mod, quest as quest_mod


class Game:

    def play(self) -> None:
        term = shutil.get_terminal_size(fallback=(80, 24))
        cols, rows = term.columns, term.lines
        win = Window(
            width=max(20, min(cols - 4, 160)),
            height=max(8, min(rows - 4, 60)),
        )

        # Passive regen handled in main loop
        state = load_state()
        player_name = state.get("player_name")
        estate_name = state.get("estate_name")
        roster_seen = state.get("roster_seen")

        ascii_lines = get_ascii_lines(cols, rows)
        inner_h = win.height

        # ── helpers ──────────────────────────────────────────────────────── #

        def _build_status_lines() -> list[str]:
            nonlocal state, roster_seen
            qi = quest_mod.quest_info()
            status: list[str] = []
            if qi.get("running"):
                rem = int(qi["remaining"])
                pct = int(min(100, qi["elapsed"] / qi["duration"] * 100))
                bw = max(10, min(40, win.width - 20))
                bar = "[" + "#" * int(bw * pct / 100) + "-" * (bw - int(bw * pct / 100)) + "]"
                status += ["", f"Quest: in progress {bar} {pct}% ({rem}s)",
                           "Leave and come back to see progress persistently."]
            elif qi.get("completed"):
                summary = quest_mod.apply_quest_damage()
                state = load_state()
                roster_seen = state.get("roster_seen")
                lines = ["", "Quest Complete!"]
                if summary["damage_taken"]:
                    lines.append("Results:")
                    for name, hp_pct, exp in summary["damage_taken"]:
                        if name in summary["fallen"]:
                            lines.append(f"   {name}: {hp_pct}% HP lost and has fallen")
                        else:
                            lines.append(f"   {name}: Lost {hp_pct}% HP and gained {exp} EXP")
                if summary["rewards"]:
                    lines.append("")
                    lines.append("Rewards:")
                    for r in summary["rewards"]:
                        lines.append(f"   {r}")
                status += lines
            return status

        def _make_greeting(pname: str | None, ename: str | None) -> tuple[str | None, str | None]:
            if not pname:
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
            import datetime
            day_seed = int(datetime.date.today().strftime("%Y%m%d"))
            rng = random.Random(day_seed)
            greeting = (
                f"Hello, {pname}" if not ename
                else f"{rng.choice(greetings)}, {pname} it's a "
                     f"{rng.choice(weathers)} day in {ename}"
            )
            return greeting, rng.choice(events)

        def _render_home(force_roster_hint: bool = False) -> None:
            status_lines = _build_status_lines()
            avail_h = max(0, inner_h - (1 if player_name else 0) - len(status_lines))
            display = [l[:win.width] for l in ascii_lines][:avail_h]
            rl: list[str] = display + [""] * 3
            gre, evt = _make_greeting(player_name, estate_name)
            if gre:
                rl.append(gre)
            if evt:
                rl.append(evt)
            if force_roster_hint or (player_name and not roster_seen):
                rl += ["", "Type 'roster' to view your roster."]
            rl += status_lines
            win.render(rl[:inner_h])

        def _show_roster() -> None:
            roster_mod.ensure_default_roster(state)
            lines = roster_mod.build_roster_lines(state)
            win.render(lines[:win.height])

        def _enter_roster_mode() -> bool:
            """Returns True if the player wants to quit the game."""
            nonlocal roster_seen
            first_visit = not roster_seen
            _show_roster()
            if first_visit:
                print(
                    "This is your roster. In your service are Hadrik and Brynndar.\n"
                    "Return to the main screen to embark on your first quest."
                )
            state["roster_seen"] = True
            save_state(state)
            roster_seen = True
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("roster> ").strip()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                parts = raw.split()
                verb  = parts[0].lower() if parts else ""
                result = roster_mod.handle_roster_command(verb, parts, state)
                if result == "quit":
                    print("Goodbye!")
                    return True
                if result == "back":
                    return False
                if result == "list":
                    _show_roster()

        def _enter_spell_mode() -> bool:
            """Returns True if the player wants to quit."""
            nonlocal state

            def _show_spells():
                spells = quest_mod.get_wizard_spells(state)
                lines = ["", "Wizard Spells:"]
                if not spells:
                    lines.append("  No wizard spells available (need a Wizard at level 3+).")
                else:
                    for i, sp in enumerate(spells, start=1):
                        status = "(Ready)" if sp["can_cast"] else f"({sp['reason']})"
                        lines.append(
                            f"  {i}. {sp['wizard']} — {sp['spell'].capitalize()}: "
                            f"{sp['desc']} {status}"
                        )
                lines += ["", "Type a number to cast, or 'back'."]
                win.render(lines[:win.height])

            _show_spells()
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("spell> ").strip()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                if not raw or raw.lower() in ("back", "b"):
                    return False
                if raw.lower() in ("quit", "exit"):
                    print("Goodbye!")
                    return True
                if raw.isdigit():
                    spells = quest_mod.get_wizard_spells(state)
                    idx = int(raw) - 1
                    if not (0 <= idx < len(spells)):
                        print(f"Invalid choice. Enter 1-{len(spells)}.")
                        continue
                    sp = spells[idx]
                    if not sp["can_cast"]:
                        print(sp["reason"])
                        continue
                    if sp["spell"] == "inspire":
                        roster = state.get("roster", [])
                        print("Choose a hero to receive 300 EXP:")
                        for j, h in enumerate(roster, start=1):
                            print(f"  {j}. {h['name']} ({h['class']}, Lvl {h['lvl']}, EXP {h.get('exp', 0)})")
                        try:
                            t_raw = win.prompt("target> ").strip()
                        except (EOFError, KeyboardInterrupt):
                            t_raw = ""
                        if not t_raw:
                            continue
                        if t_raw.isdigit():
                            tidx = int(t_raw) - 1
                            if 0 <= tidx < len(roster):
                                t_raw = roster[tidx]["name"]
                            else:
                                print("Invalid choice.")
                                continue
                        ok, msg = quest_mod.cast_wizard_spell(state, sp["wizard"], sp["spell"], t_raw)
                    else:
                        ok, msg = quest_mod.cast_wizard_spell(state, sp["wizard"], sp["spell"])
                    state = load_state()
                    print(msg)
                    _show_spells()
                else:
                    print("Type a number or 'back'.")

        def _select_party(quest_name: str) -> list | None:
            MAX_PARTY = 4
            current_roster = state.get("roster", [])
            selected: list[int] = []

            def _draw():
                lines = quest_mod.build_party_screen(quest_name, current_roster, selected, MAX_PARTY)
                win.render(lines[:win.height])

            _draw()
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("party> ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                if not raw or raw in ("back", "b"):
                    return None
                if raw in ("quit", "exit"):
                    print("Goodbye!")
                    return None
                if raw == "go":
                    if len(selected) != MAX_PARTY:
                        print(f"You must select exactly {MAX_PARTY} heroes.")
                        continue
                    return [current_roster[i] for i in selected]
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(current_roster):
                        if idx in selected:
                            selected.remove(idx)
                        elif len(selected) < MAX_PARTY:
                            selected.append(idx)
                        else:
                            print(f"Already have {MAX_PARTY} selected — deselect one first.")
                    else:
                        print(f"Invalid choice. Enter 1-{len(current_roster)}.")
                else:
                    print("Type a number to toggle, 'go' to confirm, or 'back'.")
                _draw()

        def _enter_quest_mode() -> bool:
            """Returns True if the player wants to quit the game."""
            quests, card_lines = quest_mod.build_quest_cards(state)
            win.render(card_lines[:win.height])

            while True:
                combat.apply_regen()
                try:
                    choice = win.prompt("Choose quest or 'back'> ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    choice = ""
                if not choice or choice in ("back", "b"):
                    return False
                if choice in ("quit", "exit"):
                    print("Goodbye!")
                    return True
                if choice.isdigit():
                    n = int(choice)
                    if 1 <= n <= len(quests):
                        chosen = quests[n - 1]
                        chosen["_index"] = n
                        current_roster = state.get("roster", [])
                        if chosen["name"] == "Gather Allies":
                            party = current_roster[:]
                        else:
                            party = _select_party(chosen["name"])
                            if party is None:
                                win.render(card_lines[:win.height])
                                continue
                        quest_mod.start_quest(state, chosen, party)
                        print(
                            f"Quest '{chosen['name']}' started — "
                            f"will complete in {state['quest_duration']}s "
                            f"({chosen['length']})."
                        )
                        return False
                print(f"Please choose 1-{len(quests)}, 'back', or 'quit'.")

        # ── initial render ────────────────────────────────────────────────── #
        _render_home()

        if not player_name:
            print(
                "Welcome, to the world of Venture\n"
                "You are the heir to a great legacy.\n"
                "Your once great house has fallen to the horrors from the depths.\n"
                "Gather great heroes, and cunning allies. Delve the halls of your "
                "ancestors and...\nClaim your birthright!"
            )
            try:
                name = win.prompt("What is your name? ").strip()
            except (EOFError, KeyboardInterrupt):
                name = ""
            if name:
                try:
                    estate = win.prompt("What is the name of your estate? ").strip()
                except (EOFError, KeyboardInterrupt):
                    estate = ""
                if estate:
                    state["estate_name"] = estate
                state["player_name"] = name
                save_state(state)
                player_name = name
                estate_name = state.get("estate_name")
                _render_home(force_roster_hint=True)

        # ── main command loop ─────────────────────────────────────────────── #
        while True:
            combat.apply_regen()
            try:
                cmd = win.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Goodbye!")
                return

            if not roster_seen:
                if not cmd:
                    pass
                else:
                    verb_check = cmd.split()[0].lower()
                    if verb_check in ("quit", "exit"):
                        print("Goodbye!")
                        return
                    if verb_check != "roster":
                        print("Please type 'roster' to view your roster before proceeding.")
                        continue
                    if _enter_roster_mode():
                        return
                    _render_home()
                    print('Type "quest" to view available quests.')
                    continue

            if not cmd:
                _render_home()
                continue

            parts = cmd.split()
            verb  = parts[0].lower()

            if verb == "quest":
                if quest_mod.quest_info().get("running"):
                    rem = int(quest_mod.quest_info()["remaining"])
                    print(f"Already on a quest — {rem}s remaining.")
                    continue
                if _enter_quest_mode():
                    return
                _render_home()

            elif verb == "roster":
                was_first = not roster_seen
                if _enter_roster_mode():
                    return
                _render_home()
                if was_first:
                    print('Type "quest" to view available quests.')

            elif verb == "spell":
                if _enter_spell_mode():
                    return
                _render_home()

            elif verb == "dev":
                sub = parts[1].lower() if len(parts) > 1 else ""
                if sub == "complete":
                    s = load_state()
                    if not s.get("quest_start"):
                        print("[dev] No active quest.")
                    else:
                        import time as _time
                        dur = float(s.get("quest_duration", 60))
                        s["quest_start"] = _time.time() - dur - 1
                        save_state(s)
                        print("[dev] Quest marked complete. Return to home to claim.")
                else:
                    print("[dev] Commands: dev complete")

            elif verb in ("quit", "exit"):
                print("Goodbye!")
                return

            elif verb == "help":
                print("Commands: quest, roster, spell, help, quit")

            else:
                print("Unknown command. Type 'help'.")
