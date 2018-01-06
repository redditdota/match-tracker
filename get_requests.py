import praw
from tokens import *
import matchbot
import threading
import time

APPROVED_SUBMITTERS = ["WaitForItAll", "stats95", "Gamerhcp", "772-LR", "monkeydoestoo",
                       "coronaria", "Leafeator", "Decency", "0Hellspawn0", "Intolerable"]
SUBJECTS = ["matchbot", "stop"]
TOURNAMENT_SUB = TOURNAMENT_ACCT.subreddit(SUBREDDIT)
WIKI = praw.models.WikiPage(TOURNAMENT_ACCT, "dota2", "live_matches")
REQUIRED_FIELDS = ["match_id", "post_id"]
TRACKED_POSTS = dict()

def parse_message(message):
    error = []
    values = {}
    for line in message.body.split("\n"):
        if len(line) == 0:
            continue

        parts = line.split(":")
        if len(parts) != 2:
            error.append("[bot] invalid line: " + line)
            continue
        values[parts[0].strip()] = parts[1].strip().replace("\"", "").replace("\'", "")

    if len(error) > 0:
        message.reply("\n".join(error))
        print("\n".join(error))
        message.mark_read()
        return None
    else:
        return values


def update(message):
    values = parse_message(message)
    if values is None:
        return
    print(values)

    for field in REQUIRED_FIELDS:
        if field not in values:
            reply = "[bot] missing field: " + field
            message.reply(reply)
            print(reply)
            message.mark_read()
            return

    post = values["post_id"]
    match = values["match_id"]

    if post in TRACKED_POSTS:
        message.reply("Post %s is already live updating with a match, uhoh!" % post)
        message.mark_read()
        return

    try:
        t = threading.Thread(target=matchbot.update_post, args=(post, match, ))
        t.start()
        TRACKED_POSTS[post] = t
        message.mark_read()
    except:
        print("Error: unable to start thread")


def wiki():
    while True:
        print("[bot] Updating wiki")
        games  = matchbot.get_live_league_games()
        text = []

        for game in games:
            if "radiant_team" not in game or "dire_team" not in game:
                continue
            mid = game["match_id"]
            radiant = matchbot.get_team_name(game["radiant_team"])
            dire = matchbot.get_team_name(game["dire_team"])
            text.append("%s vs %s: [%d](http://www.trackdota.com/matches/%d) | [add to existing thread](https://www.reddit.com/message/compose/?to=d2tournamentthreads&subject=matchbot&message=match_id:%%20%d\npost_id:%%20POST_ID)" % (radiant, dire, mid, mid, mid))

        WIKI.edit("\n\n".join(text), "update current live games")
        time.sleep(60)


wiki_thread = threading.Thread(target=wiki, args=())
wiki_thread.start()


while True:
    tracked = list(TRACKED_POSTS.keys())
    for post in tracked:
        if TRACKED_POSTS[post].is_alive():
            del TRACKED_POSTS[post]

    for message in TOURNAMENT_ACCT.inbox.unread():
        if message.subject not in SUBJECTS:
            continue

        if message.author not in APPROVED_SUBMITTERS:
            message.reply("[bot] Sorry, you are not an approved submitter! Please ping sushi on discord. FeelsWeirdMan")
            message.mark_read()
            continue
        else:
            print("[bot] a new message from %s!" + message.author)

        if message.subject == "matchbot":
            update(message)
        elif message.subject == "stop":
            stop(message)
        else:
            message.reply("[bot] Sorry, %s is not a valid command. Ping sushi if you're confused" % message.subject)
            message.mark_read()

    time.sleep(30)
