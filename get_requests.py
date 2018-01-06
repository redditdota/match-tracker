import praw
from tokens import *
import matchbot
import _thread
import time

APPROVED_SUBMITTERS = ["WaitForItAll", "stats95", "Gamerhcp", "772-LR",
                       "coronaria", "Leafeator", "Decency", "0Hellspawn0", "Intolerable"]
TOURNAMENT_SUB = TOURNAMENT_ACCT.subreddit(SUBREDDIT)
REQUIRED_FIELDS = ["match_id", "post_id"]
TRACKED_POSTS = dict()
TRACKED_MATCHES = dict()

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


    try:
        t = _thread.start_new_thread(matchbot.update_post, (values["post_id"], values["match_id"], ) )
        TRACKED_POSTS[values["post_id"]] = t
        TRACKED_MATCHES[values["match_id"]] = t
        message.mark_read()
    except:
        print("Error: unable to start thread")


while True:
    for message in TOURNAMENT_ACCT.inbox.unread():
        if message.author not in APPROVED_SUBMITTERS:
            message.reply("[bot] Sorry, you are not an approved submitter! Please ping sushi on discord. FeelsWeirdMan")
            message.mark_read()

        if message.subject == "matchbot":
            update(message)
        elif message.subject == "stop":
            stop(message)
        else:
            message.reply("[bot] Sorry, %s is not a valid command. Ping sushi if you're confused" % message.subject)
            message.mark_read()

    #time.sleep(60)



