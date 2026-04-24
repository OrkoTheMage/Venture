import shutil
import time
import random

from .window import Window
from .renderer import get_ascii_lines, scale_ascii
from .state import load_state, save_state, clear_state


class Game:

    def _quest_info(self):
        s = load_state()
        start = s.get("quest_start")
        if start is None:
            return {"running": False}
        try:
            start = float(start)
        except Exception:
            return {"running": False}
        now = time.time()
        elapsed = now - start
        remaining = max(0, 60 - elapsed)
        completed = elapsed >= 60
        return {
            "running": not completed,
            "elapsed": max(0, elapsed),
            "remaining": remaining,
            "completed": completed,
        }

    def play(self) -> None:
        term = shutil.get_terminal_size(fallback=(80, 24))
        cols, rows = term.columns, term.lines
        width = max(20, min(cols - 4, 160))
        height = max(8, min(rows - 4, 60))
        win = Window(width=width, height=height)

        # Load saved state (player name may be set later after initial render)
        state = load_state()
        player_name = state.get("player_name")
        estate_name = state.get("estate_name")
        roster_seen = state.get("roster_seen")

        lines = get_ascii_lines(cols, rows)
        # do not add top padding; print ascii art starting at the top
        inner_h = win.height

        # add quest status lines at bottom of display area (with progress bar)
        def _build_status_lines():
            quest = self._quest_info()
            status: list[str] = []
            if quest.get("running"):
                rem = int(quest.get("remaining", 60))
                elapsed = float(quest.get("elapsed", 0.0))
                pct = int(min(100, (elapsed / 60) * 100))
                bar_width = max(10, min(40, win.width - 20))
                filled = int(bar_width * pct / 100)
                bar = "[" + ("#" * filled) + ("-" * (bar_width - filled)) + "]"
                status.append("")
                status.append(f"Quest: in progress {bar} {pct}% ({rem}s)")
                status.append("Leave and come back to see progress persistently.")
            elif quest.get("completed"):
                status.append("")
                status.append("Quest complete! Come claim your reward.")
                clear_state()
            return status

        def _make_greeting_and_event(pname: str | None, ename: str | None) -> tuple[str | None, str | None]:
            if not pname:
                return None, None
            greetings = ["Greetings", "Hello", "Well met", "Hail"]
            weathers = ["sunny", "rainy", "stormy", "foggy", "windy", "snowy", "overcast"]
            events = [
                "A hawk circles overhead.",
                "A distant horn sounds.",
                "A sudden breeze chills you.",
                "A merchant wagon creaks by.",
                "A stray dog barks in the lane.",
                "The scent of smoke drifts from the east.",
                "Villagers whisper of a strange light.",
            ]
            if not ename:
                greeting = f"Hello, {pname}"
            else:
                greeting = f"{random.choice(greetings)}, {pname} it's a {random.choice(weathers)} day in {ename}"
            return greeting, random.choice(events)

        def _show_roster():
            # Ensure an initial roster exists in state
            roster = state.get("roster")
            if not roster:
                roster = [
                    {"name": "Hadrik", "class": "Fighter", "lvl": 1},
                    {"name": "Brynndar", "class": "Rogue", "lvl": 1},
                ]
                state["roster"] = roster
                save_state(state)

            # Load card template and substitute values for two cards
            from pathlib import Path

            tpl_path = Path(__file__).parent / "ascii" / "classCard.txt"
            try:
                tpl = tpl_path.read_text()
            except Exception:
                # fallback simple listing
                lines = [f"{h['name']} | {h['class']} | Lvl {h['lvl']}" for h in roster]
                win.render(lines[: win.height])
                return

            text = tpl
            # replace placeholders in order (left then right)
            # the inner name field in the card template is 15 chars wide
            text = text.replace("   Hero Name   ", roster[0]["name"].center(15), 1)
            text = text.replace("   Hero Name   ", roster[1]["name"].center(15), 1)
            # replace class names (assumes template contains sample classes)
            # replace first class occurrence with roster[0], second with roster[1]
            # find generic class words to replace: use the words in template
            # replace first 'Fighter' occurrence
            text = text.replace("Fighter", roster[0]["class"], 1)
            # replace next class occurrence with roster[1]
            # try common sample 'Rogue' or any remaining known class in template
            text = text.replace("Rogue", roster[1]["class"], 1)
            # replace level markers (first then second)
            text = text.replace("Lvl 1", f"Lvl {roster[0]['lvl']}", 1)
            text = text.replace("Lvl 1", f"Lvl {roster[1]['lvl']}", 1)

            lines = text.splitlines()
            win.render(lines[: win.height])

        def _enter_roster_mode():
            nonlocal roster_seen
            _show_roster()
            # mark roster as seen and persist
            state["roster_seen"] = True
            save_state(state)
            roster_seen = True
            while True:
                try:
                    rcmd = win.prompt("roster> ").strip()
                except (EOFError, KeyboardInterrupt):
                    rcmd = ""
                if not rcmd:
                    return False
                rparts = rcmd.split()
                rverb = rparts[0].lower()
                if rverb in ("back", "done"):
                    return False
                if rverb in ("quit", "exit"):
                    print("Goodbye!")
                    return True
                if rverb == "help":
                    print("Roster commands: rename [old name] [new name], list, back, quit")
                    continue
                if rverb == "list":
                    _show_roster()
                    continue
                if rverb == "rename":
                    if len(rparts) < 3:
                        print("Usage: rename [hero name] [new hero name]")
                    else:
                        old_name = rparts[1]
                        new_name = " ".join(rparts[2:])
                        roster = state.get("roster") or []
                        found = False
                        for h in roster:
                            if h.get("name", "").lower() == old_name.lower():
                                h["name"] = new_name
                                save_state(state)
                                print(f"Renamed {old_name} -> {new_name}")
                                found = True
                                break
                        if not found:
                            print(f"Hero '{old_name}' not found in roster.")
                        _show_roster()
                    continue
                print("Unknown roster command. Type 'help'.")

        # initial render
        status_lines = _build_status_lines()
        greet_lines = 1 if player_name else 0
        reserved = greet_lines + len(status_lines)
        avail_h = max(0, inner_h - reserved)
        ascii_display = [l[: win.width] for l in lines][:avail_h]
        render_lines: list[str] = ascii_display[:]
        render_lines.extend([""] * 3)
        gre, evt = _make_greeting_and_event(player_name, estate_name)
        if gre:
            render_lines.append(gre)
        if evt:
            render_lines.append(evt)
        # show roster instruction on greeting screen if needed
        if player_name and not roster_seen:
            render_lines.append("")
            render_lines.append("Type 'roster' to view your roster.")
        render_lines.extend(status_lines)
        win.render(render_lines[:inner_h])

        # show roster instruction on greeting screen; actual enforcement happens in command loop

        # If no player name yet, present the lore and prompt AFTER ascii render
        if not player_name:
            print(
                "Welcome, to the world of Venture\n"
                "You are the heir to a great legacy.\n"
                "Your once great house has fallen to the horrors from the depths.\n"
                "Gather great heroes, and cunning allies. Delve the halls of your ancestors and...\n"
                "Claim your birthright!"
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
                roster_seen = state.get("roster_seen")
                # re-render with greeting now that we have a name
                status_lines = _build_status_lines()
                greet_lines = 1
                reserved = greet_lines + len(status_lines)
                avail_h = max(0, inner_h - reserved)
                display_lines = [l[: win.width] for l in lines][:avail_h]
                render_lines = display_lines[:]
                render_lines.extend([""] * 3)
                gre, evt = _make_greeting_and_event(player_name, estate_name)
                if gre:
                    render_lines.append(gre)
                if evt:
                    render_lines.append(evt)
                # show roster instruction on greeting screen if needed
                if player_name and not roster_seen:
                    render_lines.append("")
                    render_lines.append("Type 'roster' to view your roster.")
                render_lines.extend(status_lines)
                win.render(render_lines[:inner_h])

        # Enter a minimal command loop to start quests or quit
        while True:
            try:
                cmd = win.prompt("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("Goodbye!")
                return
            if not roster_seen:
                # enforce that the player types 'roster' before any other command
                if not cmd:
                    # empty input: re-render handled below
                    pass
                else:
                    verb_check = cmd.split()[0].lower()
                    if verb_check in ("quit", "exit"):
                        print("Goodbye!")
                        return
                    if verb_check != "roster":
                        print("Please type 'roster' to view your roster before proceeding.")
                        continue
                    # user typed 'roster' — enter roster interactive mode
                    quit_now = _enter_roster_mode()
                    if quit_now:
                        return
                    continue
            if not cmd:
                # re-render to refresh progress
                status_lines = _build_status_lines()
                greet_lines = 1 if player_name else 0
                reserved = greet_lines + len(status_lines)
                avail_h = max(0, inner_h - reserved)
                display_lines = [l[: win.width] for l in lines][:avail_h]
                render_lines = display_lines[:]
                render_lines.extend([""] * 3)
                gre, evt = _make_greeting_and_event(player_name, estate_name)
                if gre:
                    render_lines.append(gre)
                if evt:
                    render_lines.append(evt)
                # show roster instruction on greeting screen if needed
                if player_name and not roster_seen:
                    render_lines.append("")
                    render_lines.append("Type 'roster' to view your roster.")
                # require roster acknowledgement after initial name/estate entry
                if not roster_seen:
                    try:
                        resp = win.prompt("Type 'roster' to view your roster: ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        resp = ""
                    while resp != "roster":
                        if resp in ("quit", "exit"):
                            print("Goodbye!")
                            return
                        try:
                            resp = win.prompt("Please type 'roster' to continue (or 'quit'): ").strip().lower()
                        except (EOFError, KeyboardInterrupt):
                            resp = ""
                    state["roster_seen"] = True
                    save_state(state)
                    roster_seen = True
                render_lines.extend(status_lines)
                win.render(render_lines[:inner_h])
                continue
            parts = cmd.split()
            verb = parts[0].lower()
            if verb == "quest":
                # start a quest if none running
                qi = self._quest_info()
                if qi.get("running"):
                    rem = int(qi.get("remaining", 60))
                    print(f"Quest already running — {rem}s remaining.")
                else:
                    # start now
                    state = {"quest_start": time.time()}
                    save_state(state)
                    print("Quest started — will complete in 60 seconds.")
                # re-render: recompute status_lines then scale ascii and render
                status_lines = _build_status_lines()
                greet_lines = 1 if player_name else 0
                reserved = greet_lines + len(status_lines)
                avail_h = max(0, inner_h - reserved)
                scaled_ascii = scale_ascii(lines, win.width, avail_h)
                display_lines = scaled_ascii
                render_lines = display_lines[:]
                render_lines.extend([""] * 3)
                gre, evt = _make_greeting_and_event(player_name, estate_name)
                if gre:
                    render_lines.append(gre)
                if evt:
                    render_lines.append(evt)
                render_lines.extend(status_lines)
                win.render(render_lines[:inner_h])
            elif verb in ("quit", "exit"):
                print("Goodbye!")
                return
            elif verb == "help":
                print("Commands: quest, roster, help, quit")
            elif verb == "roster":
                # Enter roster interactive mode
                quit_now = _enter_roster_mode()
                if quit_now:
                    return
            else:
                print("Unknown command. Type 'help'.")
