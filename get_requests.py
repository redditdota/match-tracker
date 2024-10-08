import praw
from prawcore.exceptions import RequestException
from tokens import *
import matchbot
import multiprocessing
import time
import traceback
import debug
import sys

APPROVED_SUBMITTERS = [
    "0dst",
    "coronaria",
    "Leafeator",
    "Decency",
    "0Hellspawn0",
    "Intolerable",
    "crimson589",
    "lestye",
    "JohnScofield",
    "umalpz",
    "-Trell-",
    "slurpycow112",
    "blankjanne",
    "mburst",
]
SUBJECTS = ["matchbot", "stop"]
TOURNAMENT_SUB = TOURNAMENT_ACCT.subreddit(SUBREDDIT)
WIKI = praw.models.WikiPage(TOURNAMENT_ACCT, SUBREDDIT, "live_matches")
REQUIRED_FIELDS = ["match_id", "post_id"]
TRACKED_POSTS = dict()


def log(string):
    print("[bot][%s] " % time.strftime("%c") + str(string))
    sys.stdout.flush()


def mark(message):
    for i in range(3):
        try:
            message.mark_read()
        except RequestException:
            if i >= 2:
                raise
            else:
                log(
                    "Failed to mark message from %s as unread, retrying"
                    % message.author
                )
                time.sleep(5 * i)


def parse_message(message):
    error = []
    values = {}
    for line in message.body.split("\n"):
        if len(line) == 0:
            continue

        parts = line.split(":")
        if len(parts) != 2:
            error.append("invalid line: " + line)
            continue
        values[parts[0].strip()] = parts[1].strip().replace('"', "").replace("'", "")

    if len(error) > 0:
        message.reply("\n".join(error))
        log("\n".join(error))
        mark(message)
        return None
    else:
        return values


def update(message):
    values = parse_message(message)
    if values is None:
        return
    log(values)

    for field in REQUIRED_FIELDS:
        if field not in values:
            reply = "missing field: " + field
            message.reply(reply)
            log(reply)
            mark(message)
            return

    post = values["post_id"]
    match = values["match_id"]

    if post in TRACKED_POSTS:
        message.reply(
            "Post %s is already live updating with a match, that one will be killed monkaS!"
            % post
        )
        TRACKED_POSTS[post].terminate()

    try:
        p = multiprocessing.Process(
            target=matchbot.update_post,
            args=(
                post,
                match,
            ),
        )
        p.start()
        TRACKED_POSTS[post] = p
    except:
        log("Error: unable to start thread")
        print(traceback.format_exc())

    mark(message)


def stop(message):
    post = message.body

    if post in TRACKED_POSTS:
        message.reply("Post %s will be stopped PepeHands" % post)
        TRACKED_POSTS[post].terminate()
        TRACKED_POSTS.pop(post, None)
        log("Stopping post %s" % post)
    else:
        message.reply("Post %s is not currently being updated FeelsWeirdMan" % post)

    mark(message)


def wiki():
    while True:
        log("Updating wiki")
        games = matchbot.get_live_league_games()
        text = []

        for t in games.keys():
            game_text = []
            for game in games[t]:
                if "radiant_team" not in game or "dire_team" not in game:
                    continue
                mid = game["match_id"]
                radiant = matchbot.get_team_name(game["radiant_team"])
                dire = matchbot.get_team_name(game["dire_team"])
                game_text.append(
                    "* %s vs %s: [add to existing thread](https://www.reddit.com/message/compose/?to=d2tournamentthreads&subject=matchbot&message=match_id:%%20%d\npost_id:%%20POST_ID)"
                    % (radiant, dire, mid)
                )

            if len(game_text) > 0:
                text.append("###%s\n" % t)
                text.append("\n".join(game_text))

        WIKI.edit(content="\n\n".join(text), reason="update current live games")

        log("added %d games" % len(text))

        time.sleep(60)


def check_threads():
    tracked = list(TRACKED_POSTS.keys())
    log("tracking %d posts" % len(tracked))
    for post in tracked:
        process = TRACKED_POSTS[post]
        if not process.is_alive():
            if process.exitcode != 0 or post == "wiki":
                log("process died with exitcode %d" % process.exitcode)

            del TRACKED_POSTS[post]
    log("done processing posts")


def process_messages() -> bool:
    for message in TOURNAMENT_ACCT.inbox.unread():
        if message.subject not in SUBJECTS:
            continue

        if message.author not in APPROVED_SUBMITTERS:
            message.reply(
                "Sorry, you are not an approved submitter! Please ping sushi on discord. FeelsWeirdMan"
            )
            continue
        else:
            log("a new message from %s!" % str(message.author))

        if message.subject == "matchbot":
            update(message)
        elif message.subject == "stop":
            stop(message)
        elif message.subject == "kill":
            return True
        else:
            message.reply(
                "Sorry, %s is not a valid command. Ping sushi if you're confused"
                % message.subject
            )
    return False


def start_wiki_thread():
    wiki_thread = multiprocessing.Process(target=wiki, args=())
    wiki_thread.start()
    TRACKED_POSTS["wiki"] = wiki_thread


if __name__ == "__main__":

    debug.listen()
    start_wiki_thread()

    while True:
        check_threads()
        if len(TRACKED_POSTS) == 0:
            start_wiki_thread()

        try:
            stop = process_messages()
            if stop:
                break
        except:
            log("Error processing messages")
            print(traceback.format_exc())

        time.sleep(30)
