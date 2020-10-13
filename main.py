import random
import string

import click

from client import ApiClient
from config import config
from entities import Entities
from game import run as runapp
from gameboard import GameBoard

c = ApiClient(config.api_host)


def validate_config() -> bool:
    if config.gameid == "": print('gameid cannot be empty'); return False
    if config.playerid == "": print('playerid cannot be empty'); return False

    return True


@click.group()
@click.option('--gameid', help='gameid value to use')
@click.option('--playerid', help='playerid value to use')
def cli(gameid: str, playerid: str):
    config.gameid = gameid
    config.playerid = playerid


@cli.command()
def games_get():
    games = c.get('game/')
    if games['games'] is None:
        print('no games')
        return

    for game in games['games']:
        print(f'game id: {game}')


@cli.command()
@click.option('--name', help='game name')
def games_new(name):
    game = c.post('game/new', {
        "name": name
    })

    if 'created' not in game:
        print(game)
        return

    print(f'created game with uuid: {game["uuid"]}')


@cli.command()
def games_info():
    if not validate_config():
        return

    info = c.get(f'game/info/{config.gameid}')

    if 'fow' not in info:
        print(info)
        return

    print(f'name    : {info["name"]}')
    print(f'x       : {info["size_x"]}')
    print(f'y       : {info["size_y"]}')
    print(f'fow     : {info["fow"]}')
    print(f'created : {info["created"]}')
    print(f'started : {info["started"]}')


@cli.command()
def games_join():
    if not validate_config():
        return

    join = c.post('game/join', {
        "game_id": config.gameid,
        "player_id": config.playerid
    })

    if "success" in join:
        print(f'joined status: {join["success"]}')
        return

    print(join)


@cli.command()
@click.option('--name', required=True, help='player name')
def player_register(name):
    register = c.post('player/register', {
        'name': name
    })

    if 'uuid' in register:
        print(f'your uuid is: {register["uuid"]} . keep it safe!')
        return

    print(register)


@cli.command()
def player_view():
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
    board.add_entity(Entities.Player, player["position"]["x"], player["position"]["y"])

    if surroundings["creep"] is not None:
        for creep in surroundings["creep"]:
            board.add_entity(Entities.Creep, creep["position"]["x"], creep["position"]["y"])

    if surroundings["players"] is not None:
        for player in surroundings["players"]:
            board.add_entity(Entities.Player, player["position"]["x"], player["position"]["y"])

    if surroundings["powerups"] is not None:
        for powerup in surroundings["powerups"]:
            board.add_entity(Entities.PowerUp, powerup["position"]["x"], powerup["position"]["y"])

    print(board.draw_str())


@cli.command()
@click.option('--new', is_flag=True, default=False, help='start & join a new game')
def interactive(new):
    if not new:
        if not validate_config():
            return

    if new:
        if config.playerid == "":
            print('playerid cannot be empty')

        config.gameid = c.post('game/new', {
            "name": ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
        })["uuid"]
        c.post('game/join', {
            "game_id": config.gameid,
            "player_id": config.playerid
        })
        c.put(f'game/start/{config.gameid}', {})

    runapp()


if __name__ == '__main__':
    cli()
