import praw
import requests
import sys
import itertools
import time
import math
import traceback
import datetime
import threading
import os
import cachetools.func
import pickle
import re
from tokens import *
from template import *
from teams import *
from heroes import *


START_TAG = "[](#start-match-details)"
END_TAG = "[](#end-match-details)"
GAME_NUMBER = None

LOCK = threading.Lock()


def log(*arg):
    print("[matchbot]", datetime.datetime.today().isoformat(), *arg)


def get(url):
    while True:
        try:
            response = requests.get(url)
            if response.status_code == requests.codes.ok:
                return response.json()
            else:
                log(url, response.text)
                time.sleep(10)
        except requests.exceptions.RequestException as e:
            log(url, e)
            traceback.print_exc()
            sys.stdout.flush()
        except Exception as e:
            log(url, e)
            traceback.print_exc()
            sys.stdout.flush()


def get_live_league_games():
    response = get(
        "https://api.steampowered.com/IDOTA2Match_570/GetLiveLeagueGames/v0001/?key=%s"
        % KEY
    )
    if "result" not in response:
        log("GetLiveLeagueGames Error:\n" + str(response))
        return {}

    result = response["result"]
    if result["status"] != 200:
        log("GetLiveLeagueGames Error: " + str(result["status"]))
        return {}
    else:
        games = result["games"]

        games_by_tournament = {}
        for game in games:
            t = get_tournaments().get(game["league_id"], "Unknown")
            if t not in games_by_tournament:
                games_by_tournament[t] = []
            games_by_tournament[t].append(game)

        return games_by_tournament


def get_match_detail(match_id):
    response = get(
        "https://api.steampowered.com/IDOTA2Match_570/GetMatchDetails/V001/?match_id=%s&key=%s"
        % (match_id, KEY)
    )
    if "result" not in response:
        log("GetMatchDetails Error:\n" + str(response))
        return {}

    return response["result"]


def get_player_name(account_id):
    return get_all_players().get(account_id, "")


def get_team_name(team):
    if team["team_id"] in TEAMS:
        return TEAMS[team["team_id"]]
    else:
        return team["team_name"]


def get_bans(team):
    bans = [""] * 7
    i = 0
    for hero in team.get("bans", []):
        bans[i] = HEROES[hero["hero_id"]]
        i += 1
    return bans


def get_picks(team):
    picks = [""] * 5
    i = 0
    for hero in team.get("picks", []):
        picks[i] = HEROES[hero["hero_id"]]
        i += 1
    return picks


def get_player_names(game):
    names = {}
    for player in game["players"]:
        aid = player["account_id"]
        names[aid] = get_player_name(aid)
        if names[aid] == "":
            names[aid] = player.get("name", "")
    return names


def get_player_stats(players, player_names):
    info = [["ERROR", "ERROR", -1, -1, -1, -1, -1, -1, -1, -1]] * 5
    i = 0
    for player in players:
        hero = HEROES[player["hero_id"]] if player["hero_id"] != 0 else ""
        info[i] = [
            hero,
            player_names[player["account_id"]],
            player["level"],
            player["kills"],
            player.get("death", player.get("deaths", 0)),
            player["assists"],
            player["last_hits"],
            player["denies"],
            player.get("net_worth", player.get("gold_spent", 0)),
            player["gold_per_min"],
            player["xp_per_min"],
        ]
        i += 1
    return list(itertools.chain.from_iterable(info))


def parse_live_game(game):
    global GAME_NUMBER
    GAME_NUMBER = 1 + game["radiant_series_wins"] + game["dire_series_wins"]
    text = "# Game %d \n" % GAME_NUMBER
    text += "##Live Updating...\n"

    radiant = get_team_name(game["radiant_team"])
    dire = get_team_name(game["dire_team"])

    if "scoreboard" not in game:
        return "##Pre-Draft Phase\n"

    scoreboard = game["scoreboard"]
    duration = scoreboard["duration"]

    if duration == 0:
        text += "##In Draft Phase"
    else:
        text += "##Duration: %02d:%02d" % (math.floor(duration / 60), duration % 60)

    text += SCORE_BOARD % (
        radiant,
        scoreboard["radiant"]["score"],
        scoreboard["dire"]["score"],
        dire,
    )
    text += "\n"

    rb = get_bans(scoreboard["radiant"])
    db = get_bans(scoreboard["dire"])
    text += BANS % (
        radiant,
        rb[0],
        rb[1],
        db[0],
        db[1],
        dire,
        rb[2],
        rb[3],
        rb[4],
        db[2],
        db[3],
        db[4],
        rb[5],
        rb[6],
        db[5],
        db[6],
    )
    text += "\n"

    rp = get_picks(scoreboard["radiant"])
    dp = get_picks(scoreboard["dire"])
    text += PICKS % (
        radiant,
        rp[0],
        rp[1],
        dp[0],
        dp[1],
        dire,
        rp[2],
        rp[3],
        dp[2],
        dp[3],
        rp[4],
        dp[4],
    )
    text += "\n"

    player_names = get_player_names(game)
    rplayers = get_player_stats(scoreboard["radiant"]["players"], player_names)
    dplayers = get_player_stats(scoreboard["dire"]["players"], player_names)
    text += LIVE % (*rplayers, *dplayers)
    text += "\n"
    text += "_____"
    text += "\n"

    return text


def get_live_match_info(match_id):
    match_id = int(match_id)
    games_by_tournament = get_live_league_games()

    for games in games_by_tournament.values():
        for game in games:
            if "match_id" in game and game["match_id"] == match_id:
                return parse_live_game(game)

    return ""


def get_completed_match_info(match_id):
    match_id = int(match_id)
    game = get_match_detail(match_id)

    if "radiant_win" not in game:
        # game not actually completed
        return ""

    radiant = (
        TEAMS[game["radiant_team_id"]]
        if game.get("radiant_team_id", "missing") in TEAMS
        else game.get("radiant_name", "Radiant")
    )
    dire = (
        TEAMS[game["dire_team_id"]]
        if game.get("dire_team_id", "missing") in TEAMS
        else game.get("dire_name", "Dire")
    )

    victor = ""
    if game["radiant_win"] == 1:
        if "logo" in radiant:
            victor = radiant + " " + game["radiant_name"]
        else:
            victor = radiant
    else:
        if "logo" in dire:
            victor = dire + " " + game["dire_name"]
        else:
            victor = dire

    text = "# Game %d\n" % GAME_NUMBER
    text += "##%s Victory!\n" % victor

    duration = game["duration"]
    text += "##Duration: %02d:%02d" % (math.floor(duration / 60), duration % 60)

    text += SCORE_BOARD % (radiant, game["radiant_score"], game["dire_score"], dire)
    text += "\n"

    rb = [""] * 7
    db = [""] * 7
    rp = [""] * 5
    dp = [""] * 5

    rb_idx = 0
    db_idx = 0
    rp_idx = 0
    dp_idx = 0

    for pb in game.get("picks_bans", []):
        if pb["is_pick"]:
            if pb["team"] == 0:
                rp[rp_idx] = HEROES[pb["hero_id"]]
                rp_idx += 1
            else:
                dp[dp_idx] = HEROES[pb["hero_id"]]
                dp_idx += 1
        else:
            if pb["team"] == 0:
                rb[rb_idx] = HEROES[pb["hero_id"]]
                rb_idx += 1
            else:
                db[db_idx] = HEROES[pb["hero_id"]]
                db_idx += 1

    text += BANS % (
        radiant,
        rb[0],
        rb[1],
        db[0],
        db[1],
        dire,
        rb[2],
        rb[3],
        rb[4],
        db[2],
        db[3],
        db[4],
        rb[5],
        rb[6],
        db[5],
        db[6],
    )
    text += "\n"
    text += PICKS % (
        radiant,
        rp[0],
        rp[1],
        dp[0],
        dp[1],
        dire,
        rp[2],
        rp[3],
        dp[2],
        dp[3],
        rp[4],
        dp[4],
    )
    text += "\n"

    player_names = get_player_names(game)

    rplayers = get_player_stats(
        [player for player in game["players"] if player["player_slot"] < 5],
        player_names,
    )
    dplayers = get_player_stats(
        [player for player in game["players"] if player["player_slot"] > 5],
        player_names,
    )
    text += END % (*rplayers, *dplayers)
    text += "\n"

    text += (
        "More information on [Dotabuff](http://dotabuff.com/matches/%d), \
    [OpenDota](https://www.opendota.com/matches/%d), \
    and [datDota](http://datdota.com/matches/%d)"
        % (match_id, match_id, match_id)
    )

    text += "\n"
    text += "_____"
    text += "\n"

    return text


def _update_post(post_id, match_id):
    post = TOURNAMENT_ACCT.submission(post_id)
    log("Attempting to update '%s' for match %s" % (post.title, match_id))

    body = post.selftext
    start_idx = body.find(START_TAG)
    end_idx = body.find(END_TAG)

    finished = False
    match_info = get_live_match_info(match_id)
    new_body = ""
    if len(match_info) == 0:
        log("Not a live match...?")
        global GAME_NUMBER
        if GAME_NUMBER is None:
            game_numbers = re.findall("Game ([0-9]+)", body[:start_idx])
            if len(game_numbers) > 0:
                GAME_NUMBER = int(game_numbers[-1]) + 1
            else:
                GAME_NUMBER = 1

        match_info = get_completed_match_info(match_id)
        if len(match_info) > 0:
            new_body = (
                body[:start_idx]
                + "\n"
                + match_info
                + "\n"
                + START_TAG
                + "\n"
                + body[end_idx:]
            )
            finished = True
            log("Match completed")
        else:
            finished = False
    else:
        new_body = (
            body[: start_idx + len(START_TAG)]
            + "\n"
            + match_info
            + "\n"
            + body[end_idx:]
        )
        finished = False

    if len(match_info) > 0:
        post.edit(new_body)
    else:
        log("Skip updating this cycle")
    return finished


def update_post(post_id, match_id):
    finished = False
    while not finished:
        try:
            with LOCK:
                finished = _update_post(post_id, match_id)
                time.sleep(30)
        except Exception as e:
            log("Error " + str(e))
            traceback.print_exc()
            sys.stdout.flush()
            pass


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)
def get_all_players() -> dict:
    os.makedirs("cache", exist_ok=True)
    if os.path.exists("cache/players.pkl"):
        with open("cache/players.pkl", "rb") as f:
            (last_update, cache) = pickle.load(f)
            if last_update <= datetime.datetime.today().date():
                return cache

    info = get("https://www.dota2.com/webapi/IDOTA2Fantasy/GetProPlayerInfo/v001")
    if "player_infos" in info:
        pro_player_names = {}
        for player in info["player_infos"]:
            pro_player_names[player["account_id"]] = player["name"]
        log("pro player cache updated:", len(pro_player_names))

        with open("cache/players.pkl", "wb") as f:
            pickle.dump((datetime.datetime.today().date(), pro_player_names), f)

        return pro_player_names
    return {}


@cachetools.func.ttl_cache(maxsize=128, ttl=60 * 60)
def get_tournaments() -> dict:
    os.makedirs("cache", exist_ok=True)
    if os.path.exists("cache/tournaments.pkl"):
        with open("cache/tournaments.pkl", "rb") as f:
            (last_update, cache) = pickle.load(f)
            if last_update <= datetime.datetime.today().date():
                return cache

    info = get("https://www.dota2.com/webapi/IDOTA2DPC/GetLeagueInfoList/v0001/")
    if "infos" in info:
        tournament_list = {}
        for tournament in info["infos"]:
            if tournament["status"] == 3:
                tournament_list[tournament["league_id"]] = tournament["name"]
        log("active tournament list updated:", len(tournament_list))

        with open("cache/tournaments.pkl", "wb") as f:
            pickle.dump((datetime.datetime.today().date(), tournament_list), f)

        return tournament_list
    else:
        return {}


def main(argv):
    finished = False
    while not finished:
        try:
            finished = _update_post(argv[1], argv[2])
        except Exception as e:
            log("Error " + str(e))
            traceback.print_exc()
            sys.stdout.flush()
            pass
        time.sleep(30)


if __name__ == "__main__":
    main(sys.argv)
