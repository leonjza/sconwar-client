# from: https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/examples/full-screen/split-screen.py
import asyncio
import time

from prompt_toolkit.application import Application
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout

from client import ApiClient
from config import config
from entities import Entities
from gameboard import GameBoard

c = ApiClient(config.api_host)

action_completer = WordCompleter([
    'attack ', 'move ', 'pickup ', 'use '
], ignore_case=True)

# 3. Create the buffers
#    ------------------

board_buffer = Buffer()
player_buffer = Buffer()
log_buffer = Buffer()
action_buffer = Buffer(name="action",
                       multiline=False, completer=action_completer,
                       auto_suggest=AutoSuggestFromHistory(),
                       enable_history_search=True)

# 1. First we create the layout
#    --------------------------

board_window = Window(BufferControl(buffer=board_buffer))
player_window = Window(BufferControl(buffer=player_buffer))
log_window = Window(BufferControl(buffer=log_buffer))
action_window = Window(BufferControl(buffer=action_buffer))

left_window = HSplit(
    [
        board_window,
        Window(height=1, char="-", style="class:line"),
        player_window
    ]
)

right_window = HSplit(
    [
        log_window,
        Window(height=1, char="-", style="class:line"),
        action_window
    ]
)

body = VSplit(
    [
        left_window,
        # A vertical line in the middle. We explicitly specify the width, to make
        # sure that the layout engine will not try to divide the whole width by
        # three for all these windows.
        Window(width=1, char="|", style="class:line"),
        # Display the Result buffer on the right.
        right_window,
    ]
)

# default buffer texts
board_buffer_text = "press ctrl+r to start"
log_buffer_text = "press ctrl+r to start"
action_buffer_text = "commands: (m)ove, (a)ttack, (p)ickup <direction / x,y>"

board_buffer.text = board_buffer_text
log_buffer.text = log_buffer_text
action_buffer.text = action_buffer_text


# helpers to call functions in the background

def call_in_background(target, *, loop=None, executor=None):
    """Schedules and starts target callable as a background task

    If not given, *loop* defaults to the current thread's event loop
    If not given, *executor* defaults to the loop's default executor

    Returns the scheduled task.
    """
    if loop is None:
        loop = asyncio.get_event_loop()
    if callable(target):
        return loop.run_in_executor(executor, target)
    raise TypeError("target must be a callable, "
                    "not {!r}".format(type(target)))


# As a demonstration. Let's add a title bar to the top, displaying "Hello world".

# somewhere, because usually the default key bindings include searching. (Press
# Ctrl-R.) It would be really annoying if the search key bindings are handled,
# but the user doesn't see any feedback. We will add the search toolbar to the
# bottom by using an HSplit.


def get_titlebar_text():
    return [
        ("class:title", " sconwar-client "),
        ("class:title", " (press ctrl-q to quit.)"),
    ]


root_container = HSplit(
    [
        # The titlebar.
        Window(
            height=1,
            content=FormattedTextControl(get_titlebar_text),
            align=WindowAlign.CENTER,
        ),
        # Horizontal separator.
        Window(height=1, char="-", style="class:line"),
        # The 'body', like defined above.
        body,
    ]
)

# 2. Adding key bindings
#   --------------------

# As a demonstration, we will add just a ControlQ key binding to exit the
# application.  Key bindings are registered in a
# `prompt_toolkit.key_bindings.registry.Registry` instance. We use the
# `load_default_key_bindings` utility function to create a registry that
# already contains the default key bindings.

kb = KeyBindings()


# kb.add("tab")(focus_next)
# kb.add("s-tab")(focus_previous)


# Now add the Ctrl-Q binding. We have to pass `eager=True` here. The reason is
# that there is another key *sequence* that starts with Ctrl-Q as well. Yes, a
# key binding is linked to a sequence of keys, not necessarily one key. So,
# what happens if there is a key binding for the letter 'a' and a key binding
# for 'ab'. When 'a' has been pressed, nothing will happen yet. Because the
# next key could be a 'b', but it could as well be anything else. If it's a 'c'
# for instance, we'll handle the key binding for 'a' and then look for a key
# binding for 'c'. So, when there's a common prefix in a key binding sequence,
# prompt-toolkit will wait calling a handler, until we have enough information.

# Now, There is an Emacs key binding for the [Ctrl-Q Any] sequence by default.
# Pressing Ctrl-Q followed by any other key will do a quoted insert. So to be
# sure that we won't wait for that key binding to match, but instead execute
# Ctrl-Q immediately, we can pass eager=True. (Don't make a habit of adding
# `eager=True` to all key bindings, but do it when it conflicts with another
# existing key binding, and you definitely want to override that behaviour.


@kb.add("c-c", eager=True)
@kb.add("c-q", eager=True)
def _(event):
    """
    Pressing Ctrl-Q or Ctrl-C will exit the user interface.
    Setting a return value means: quit the event loop that drives the user
    interface and return this value from the `Application.run()` call.
    Note that Ctrl-Q does not work on all terminals. Sometimes it requires
    executing `stty -ixon`.
    """
    event.app.exit()


# flag used to knw if we have called ^s already
started = False


@kb.add("c-r", eager=True)
def _(_):
    call_in_background(board_view)
    call_in_background(player_view)
    call_in_background(game_events)


@kb.add("c-e", eager=True)
@kb.add("enter", eager=True)
def _(_):
    parse_command()


# Now we add an event handler that captures change events to the buffer on the
# left. If the text changes over there, we'll update the buffer on the right.

# ------------
def board_view():
    while True:
        info = c.get(f'game/info/{config.gameid}')
        if 'fow' not in info:
            print(info)
            return

        surroundings = c.post('player/surroundings', {
            "game_id": config.gameid,
            "player_id": config.playerid
        })
        if 'creep' not in surroundings:
            print(surroundings)
            return

        player = c.post('player/status', {
            "game_id": config.gameid,
            "player_id": config.playerid
        })
        if 'player' not in player:
            print(player)
            return
        player = player["player"]

        board = GameBoard(info["size_x"], info["size_y"])
        board.add_entity(Entities.Player,
                         player["position"]["x"], player["position"]["y"])

        if surroundings["creep"] is not None:
            for creep in surroundings["creep"]:
                board.add_entity(Entities.Creep,
                                 creep["position"]["x"], creep["position"]["y"])

        if surroundings["players"] is not None:
            for player in surroundings["players"]:
                board.add_entity(Entities.Player,
                                 player["position"]["x"], player["position"]["y"])

        if surroundings["powerups"] is not None:
            for powerup in surroundings["powerups"]:
                board.add_entity(Entities.PowerUp,
                                 powerup["position"]["x"], powerup["position"]["y"])

        board_buffer.text = board.draw_str()
        time.sleep(1)


def player_view():
    powerup_types = {
        0: "health",
        1: "teleport",
        2: "doubledmg"
    }

    while True:
        player = c.post('player/status', {
            "game_id": config.gameid,
            "player_id": config.playerid
        })["player"]

        game = c.get(f'game/info/{config.gameid}')

        player_buffer.text = f'{player["name"]} health: ({player["health"]}/100)\n'
        player_buffer.text += f'actions: {player["action_count"]}/2 position: x={player["position"]["x"]},y={player["position"]["y"]}\n'

        if player["buffs"] is not None:
            player_buffer.text += f'buffs: {len(player["buffs"])} '
            for buff in player["buffs"]:
                player_buffer.text += f'[{powerup_types[buff]}]'
            player_buffer.text += '\n'

        if player["powerups"] is not None:
            player_buffer.text += f'powerups: {len(player["powerups"])}\n'
            for powerup in player["powerups"]:
                player_buffer.text += f' ! powerup {powerup_types[powerup["type"]]} -> {powerup["id"]}\n'

        player_buffer.text += f'game name: {game["name"]}\n'
        player_buffer.text += f'alive creep/players ' \
                              f'{game["game_entities"]["alive_creep"]}/' \
                              f'{game["game_entities"]["alive_players"]}\n'
        if config.playerid == game["current_player"]:
            player_buffer.text += f'game curr player: IT IS OUR ROUND!\n'
        else:
            player_buffer.text += f'game curr player: {game["current_player"]}\n'
        time.sleep(1)


def game_events():
    while True:
        events = c.get(f'game/events/{config.gameid}')
        if 'events' not in events:
            print(events)
            return

        log_buffer.text = ""

        sorted_events = sorted(events["events"], key=lambda i: i["ID"], reverse=True)[:500]
        for e in sorted_events:
            d1 = e["date_created"].split("-")
            d = d1[2].split("+")[0]
            log_buffer.text += " -> ".join([d, e["msg"]]) + "\n"
        time.sleep(1)


def parse_command():
    """
        A simple command parser for sconwar
    """

    def direction(directions: str) -> (int, int):
        player = c.post('player/status', {
            "game_id": config.gameid,
            "player_id": config.playerid
        })
        x, y = player["player"]["position"]["x"], player["player"]["position"]["y"]

        directions = directions.split(' ')[1:]

        for d in directions:
            if ',' in d:
                x, y = d.split(',')
            if d == "left":
                x -= 1
            if d == "right":
                x += 1
            if d == "up":
                y += 1
            if d == "down":
                y -= 1

        return int(x), int(y)

    cmd = action_buffer.text.strip()

    if len(cmd) == 0 or len(cmd.split()) < 2:
        return

    what = cmd.split(' ')[0]

    if what in 'move':
        new_x, new_y = direction(cmd)
        # post move command
        r = c.post('action/move', {
            "game_player_id": {
                "game_id": config.gameid,
                "player_id": config.playerid
            },
            "x": new_x, "y": new_y,
        })

        if 'success' not in r:
            log_buffer.text += str(r)

    if what in 'attack':
        target_x, target_y = direction(cmd)
        # post attack command
        r = c.post('action/attack', {
            "game_player_id": {
                "game_id": config.gameid,
                "player_id": config.playerid
            },
            "x": target_x, "y": target_y,
        })

        if 'success' not in r:
            log_buffer.text += str(r)

    if what in 'pickup':
        target_x, target_y = direction(cmd)
        # post pickup command
        r = c.post('action/pickup', {
            "game_player_id": {
                "game_id": config.gameid,
                "player_id": config.playerid
            },
            "x": target_x, "y": target_y,
        })

        if 'success' not in r:
            log_buffer.text += str(r)

    if what in 'use':
        powerup_id = cmd.split(' ')[1]
        # post use command
        r = c.post('action/use', {
            "game_player_id": {
                "game_id": config.gameid,
                "player_id": config.playerid
            },
            "powerup_id": powerup_id,
        })

        if 'success' not in r:
            log_buffer.text += str(r)

    action_buffer.text = ""


# ------------


# 3. Creating an `Application` instance
#    ----------------------------------

# This glues everything together.

application = Application(
    layout=Layout(root_container, focused_element=action_window),
    key_bindings=kb,
    # Let's add mouse support!
    mouse_support=True,
    # Using an alternate screen buffer means as much as: "run full screen".
    # It switches the terminal to an alternate screen.
    full_screen=True,
)


# 4. Run the application
#    -------------------


def run():
    # Run the interface. (This runs the event loop until Ctrl-Q is pressed.)
    application.run()


if __name__ == "__main__":
    run()
