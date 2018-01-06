import praw
from tokens import *
import matchbot
import _thread

APPROVED_SUBMITTERS = ["WaitForItAll", "stats95", "Gamerhcp", "772-LR",
                       "coronaria", "Leafeator", "Decency", "0Hellspawn0", "Intolerable"]
TOURNAMENT_SUB = TOURNAMENT_ACCT.subreddit(SUBREDDIT)
REQUIRED_FIELDS = ["match_id", "post_id"]

while True:
    for message in TOURNAMENT_ACCT.inbox.unread():
        if "matchbot" in message.subject and message.author in APPROVED_SUBMITTERS:
            values = {}
            for line in message.body.split("\n"):
                if len(line) == 0:
                    continue

                parts = line.split(":")
                if len(parts) != 2:
                    reply = "[bot] invalid line: " + line
                    message.reply(reply)
                    print(reply)
                    continue

                values[parts[0].strip()] = parts[1].strip().replace("\"", "").replace("\'", "")

            for field in REQUIRED_FIELDS:
                if field not in values:
                    reply = "[bot] missing field: " + field
                    message.reply(reply)
                    print(reply)
                    continue

            print(values)

            try:
                _thread.start_new_thread(matchbot.update_post, (values["post_id"], values["match_id"], ) )
                message.mark_read()
            except:
                print("Error: unable to start thread")
    time.sleep(60)
