import random
import shutil
import shlex

from .window import Window
from .renderer import get_ascii_lines
from .state import load_state, save_state
from . import combat, roster as roster_mod, quest as quest_mod, journal as journal_mod
try:
    from . import dev as dev_mod
except ImportError:
    dev_mod = None


class Game:

    def play(self) -> None:
        term = shutil.get_terminal_size(fallback=(80, 24))
        cols, rows = term.columns, term.lines
        compact = rows < 45 or cols < 115
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
                    for name, hp_pct, exp, leveled_to in summary["damage_taken"]:
                        if name in summary["fallen"]:
                            lines.append(f"   {name}: Lost {hp_pct}% HP and has fallen")
                        elif leveled_to is not None:
                            lines.append(f"   {name}: Lost {hp_pct}% HP and gained {exp} EXP. Leveling up to LVL {leveled_to}")
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
            gold = int(state.get("gold", 0))
            week = int(state.get("week", 0))
            stats_line = f"Coffers: {gold}G  |  Week: {week}"
            stats_extra = 3 if (player_name and estate_name) else 0
            greeting_lines = 2 if player_name else 0
            _hints: list[str] = []
            if force_roster_hint or (player_name and not roster_seen):
                _hints.append('Type "roster" to view your roster.')
            if player_name and state.get("gather_allies_done") and not state.get("recruit_hint_seen"):
                _hints.append('Type "recruit" to see a list of recruitable party members')
            _has_lvl2_wiz = any(
                h.get("class") == "Wizard" and int(h.get("lvl", 1)) >= 2
                for h in state.get("roster", [])
            )
            if player_name and _has_lvl2_wiz and not state.get("spells_hint_seen"):
                _hints.append('Type "spells" to see a list of castable spells')
            if player_name and state.get("graveyard") and not state.get("graveyard_hint_seen"):
                _hints.append('Type "graveyard" to see a list of fallen heros')
            # Show journal hint if the player has completed at least one journal item
            try:
                j_entries = journal_mod.get_journal_entries(state)
                if player_name and any(e.get("done") for e in j_entries) and not state.get("journal_hint_seen"):
                    _hints.append('Type "journal" to see a list of goals for the estate.')
            except Exception:
                pass
            hint_lines = len(_hints) * 2  # blank line + text per hint
            avail_h = max(0, inner_h - 1 - stats_extra - greeting_lines - hint_lines - len(status_lines))
            display = [l[:win.width] for l in ascii_lines][:avail_h]
            logo_width = max((len(l.rstrip()) for l in display), default=0)
            if logo_width > len(stats_line):
                stats_line = stats_line.center(logo_width)
            stats_line = f"\033[1m{stats_line}\033[0m"
            rl: list[str] = display + [""]
            if player_name and estate_name:
                rl.append(stats_line)
                rl += ["", ""]
            gre, evt = _make_greeting(player_name, estate_name)
            if gre:
                rl.append(gre)
            if evt:
                rl.append(evt)
            for _hint in _hints:
                rl += ["", _hint]
            rl += status_lines
            win.render(rl[:inner_h])

        def _show_roster(page: int = 0) -> None:
            roster_mod.ensure_default_roster(state)
            lines = roster_mod.build_roster_lines(state, page, compact=compact)
            win.render(lines[:win.height])

        def _enter_roster_mode() -> bool:
            """Returns True if the player wants to quit the game."""
            nonlocal roster_seen
            current_page = 0
            first_visit = not roster_seen
            _show_roster(current_page)
            if first_visit:
                print(
                    "\nThis is your roster. In your service are Hadrik and Brynndar.\n"
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
                try:
                    parts = shlex.split(raw)
                except ValueError:
                    parts = raw.split()
                verb  = parts[0].lower() if parts else ""
                # Page navigation: a bare digit navigates to that roster page
                if verb.isdigit():
                    total = roster_mod.get_roster_page_count(state)
                    p = int(verb) - 1
                    if 0 <= p < total:
                        current_page = p
                        _show_roster(current_page)
                    else:
                        print(f"Invalid page. Enter 1-{total}.")
                    continue
                result = roster_mod.handle_roster_command(verb, parts, state)
                if result == "quit":
                    print("Goodbye!")
                    return True
                if result == "back":
                    return False
                if result == "list":
                    _show_roster(current_page)

        def _enter_spell_mode() -> bool:
            """Returns True if the player wants to quit."""
            nonlocal state
            # Block opening the spells view while a quest is active
            qi = quest_mod.quest_info()
            if qi.get("running"):
                lines = ["", "Cannot cast spells while a quest is in progress", ""]
                win.render(lines[:win.height])
                try:
                    _ = win.prompt("spells> ", hint="Press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                return False

            def _show_spells(msg: str = ""):
                lines = quest_mod.build_spell_card_lines(state, compact=compact)
                if msg:
                    lines += ["", f"  {msg}"]
                win.render(lines[:win.height])

            _show_spells()
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("spells> ", hint="Type a number to cast, or press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                if not raw or raw.lower() in ("back", "b"):
                    return False
                if raw.lower() in ("quit", "exit"):
                    print("Goodbye!")
                    return True
                if not raw.isdigit():
                    continue

                spells = quest_mod.get_available_spells(state)
                idx = int(raw) - 1
                if not (0 <= idx < len(spells)):
                    print(f"Invalid choice. Enter 1-{len(spells)}.")
                    continue
                chosen_spell = spells[idx]
                if not chosen_spell["can_cast"]:
                    print(chosen_spell["reason"])
                    continue

                # ── pick caster ───────────────────────────────────────────── #
                casters = quest_mod.get_casters_for_spell(state, chosen_spell["spell"])
                if len(casters) == 1:
                    caster = casters[0]
                else:
                    caster_lines = ["", f"Choose a caster for {chosen_spell['spell_label']}:"]
                    for j, c in enumerate(casters, start=1):
                        status = "(Ready)" if c["can_cast"] else f"({c['reason']})"
                        caster_lines.append(f"  {j}. {c['wizard']} {status}")
                    win.render(caster_lines[:win.height])
                    try:
                        c_raw = win.prompt("spells> ", hint="Choose a caster or press 'ENTER' to cancel").strip()
                    except (EOFError, KeyboardInterrupt):
                        c_raw = ""
                    if not c_raw:
                        _show_spells()
                        continue
                    if not c_raw.isdigit() or not (1 <= int(c_raw) <= len(casters)):
                        print("Invalid choice.")
                        _show_spells()
                        continue
                    caster = casters[int(c_raw) - 1]

                if not caster["can_cast"]:
                    print(f"{caster['wizard']} cannot cast this spell: {caster['reason']}")
                    _show_spells()
                    continue

                # ── pick target (if needed) ───────────────────────────────── #
                target_name = None
                if chosen_spell["target"] == "Other":
                    roster = state.get("roster", [])
                    mage_armor_map = state.get("mage_armor", {})
                    import time as _time
                    now = _time.time()
                    if chosen_spell["spell"] == "mage_armor":
                        targets = [h for h in roster if mage_armor_map.get(h["name"], 0) <= now]
                    elif chosen_spell["spell"] == "inspire":
                        from .combat import exp_to_level as _etl
                        MAX_LVL = 5
                        targets = [h for h in roster if int(h.get("lvl", 1)) < MAX_LVL]
                    else:
                        targets = roster
                    if not targets:
                        _show_spells("No valid targets available.")
                        continue
                    target_lines = ["", f"Choose a target for {chosen_spell['spell_label']}:"]
                    for j, h in enumerate(targets, start=1):
                        target_lines.append(f"  {j}. {h['name']} ({h['class']}, Lvl {h['lvl']}, HP {int(float(h.get('hp',100))/max(1.0,float(h.get('max_hp',100)))*100)}%)")
                    win.render(target_lines[:win.height])
                    try:
                        t_raw = win.prompt("spells> ", hint="Choose a target or press 'ENTER' to cancel").strip()
                    except (EOFError, KeyboardInterrupt):
                        t_raw = ""
                    if not t_raw:
                        _show_spells()
                        continue
                    if t_raw.isdigit():
                        tidx = int(t_raw) - 1
                        if 0 <= tidx < len(targets):
                            target_name = targets[tidx]["name"]
                        else:
                            print("Invalid choice.")
                            _show_spells()
                            continue
                    else:
                        target_name = t_raw

                ok, msg = quest_mod.cast_wizard_spell(state, caster["wizard"], chosen_spell["spell"], target_name)
                state = load_state()
                _show_spells(msg)

        def _enter_recruit_mode() -> bool:
            """Returns True if the player wants to quit."""
            nonlocal state

            def _show_recruits():
                offers = quest_mod.build_recruit_offers(state)
                gold = int(state.get("gold", 0))
                lines = [f"  Gold: {gold}G"] + roster_mod.build_recruit_card_lines(offers, compact=compact)
                win.render(lines[:win.height])

            _show_recruits()
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("recruit> ", hint="Type a number to hire, or press 'ENTER' to return").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                if not raw or raw in ("back", "b"):
                    return False
                if raw in ("quit", "exit"):
                    print("Goodbye!")
                    return True
                if raw.isdigit():
                    idx = int(raw) - 1
                    ok, msg = quest_mod.hire_recruit(state, idx)
                    state = load_state()
                    print(msg)
                    if ok:
                        _show_recruits()

        def _select_party(quest_name: str, max_party: int = 4, enemy_types: str = "", danger: int = 0, length: str = "Short") -> list | None:
            MAX_PARTY = max_party
            current_roster = state.get("roster", [])
            selected: list[int] = []

            def _draw():
                lines = quest_mod.build_party_screen(
                    quest_name, current_roster, selected, MAX_PARTY,
                    win.width, enemy_types, danger, length, state=state
                )
                win.render(lines[:win.height])

            _draw()
            while True:
                combat.apply_regen()
                try:
                    raw = win.prompt("quest> ", hint="Type a number to toggle, 'venture' to confirm, or press 'ENTER' to return").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    raw = ""
                if not raw or raw in ("back", "b"):
                    return None
                if raw in ("quit", "exit"):
                    print("Goodbye!")
                    return None
                if raw == "venture":
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
                _draw()

        def _enter_quest_mode() -> bool:
            """Returns True if the player wants to quit the game."""
            quests, card_lines = quest_mod.build_quest_cards(state, compact=compact)
            win.render(card_lines[:win.height])

            while True:
                combat.apply_regen()
                try:
                    choice = win.prompt("quest> ", hint="Type a number to choose a quest or press 'ENTER' to return").strip().lower()
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
                        enemies = chosen.get("enemies", "")
                        danger = int(chosen.get("danger", 0))
                        if chosen["name"] == "Gather Allies":
                            n_heroes = len(state.get("roster", []))
                            party = _select_party(
                                chosen["name"], max_party=n_heroes,
                                enemy_types=enemies, danger=danger,
                                length=chosen.get("length", "Short")
                            )
                        else:
                            party = _select_party(
                                chosen["name"], enemy_types=enemies,
                                danger=danger, length=chosen.get("length", "Short")
                            )
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
        skip_prompt = False
        while True:
            combat.apply_regen()
            try:
                if skip_prompt:
                    cmd = ""
                    skip_prompt = False
                else:
                    cmd = win.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Goodbye!")
                return

            if not roster_seen:
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
                    if _enter_roster_mode():
                        return
                    _render_home()
                    print("\nType \"quest\" to view available quests.")
                    continue

            if not cmd:
                _render_home()
                continue

            try:
                parts = shlex.split(cmd)
            except ValueError:
                parts = cmd.split()
            verb  = parts[0].lower() if parts else ""

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
                    print("\nType \"quest\" to view available quests.")

            elif verb == "spells":
                state["spells_hint_seen"] = True
                save_state(state)
                if quest_mod.quest_info().get("running"):
                    print("Cannot cast spells while a quest is in progress.")
                    continue
                if _enter_spell_mode():
                    return
                _render_home()

            elif verb == "recruit":
                if not state.get("gather_allies_done"):
                    print("Your best chance to gather allies right now is on a quest — look for 'Gather Allies' in the quest list.")
                    continue
                if quest_mod.quest_info().get("running"):
                    print("Cannot recruit while a quest is in progress.")
                    continue
                roster_size = len(state.get("roster", []))
                if roster_size >= roster_mod.ROSTER_CAP:
                    print(f"Roster is full ({roster_mod.ROSTER_CAP}/{roster_mod.ROSTER_CAP}). Dismiss a hero in the roster menu first.")
                    continue
                state["recruit_hint_seen"] = True
                save_state(state)
                if _enter_recruit_mode():
                    return
                _render_home()

            elif verb == "dev":
                if dev_mod is None:
                    print("Unknown command. Type 'help'.")
                else:
                    state = dev_mod.handle_dev_command(parts, state, cols, rows, compact)

            elif verb in ("quit", "exit"):
                print("Goodbye!")
                return

            elif verb == "graveyard":
                state["graveyard_hint_seen"] = True
                save_state(state)
                lines = quest_mod.build_graveyard_lines(state)
                win.render(lines[:win.height])
                try:
                    _ = win.prompt("graveyard> ", hint="Press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                _render_home()
                skip_prompt = True

            elif verb == "journal":
                state["journal_hint_seen"] = True
                save_state(state)
                lines = journal_mod.build_journal_lines(state)
                win.render(lines[:win.height])
                try:
                    _ = win.prompt("journal> ", hint="Press 'ENTER' to return").strip()
                except (EOFError, KeyboardInterrupt):
                    pass
                _render_home()
                skip_prompt = True
                _render_home()
                skip_prompt = True

            elif verb == "help":
                print("Commands: quest, roster, recruit, spells, graveyard, journal, help, quit")

            else:
                print("Unknown command. Type 'help'.")
