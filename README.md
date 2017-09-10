Create a file called "tokens.py" with

```
KEY = <Steam Web API Key>

SUBREDDIT = "dota2"
REDDIT_CLIENT_SECRET = "secret"
REDDIT_CLIENT_ID = "client_id"

TOURNAMENT_USER = "D2TournamentThreads"
TOURNAMENT_PWD = <D2TournamentThreads password>

MOD = <mod username>
MOD_PWD = <mod password>

TOURNAMENT_ACCT = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
            username=TOURNAMENT_USER,
                password=TOURNAMENT_PWD,
                    user_agent="match bot")

MOD_ACCT = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
            username=MOD,
                password=MOD_PWD,
                    user_agent="match bot")


```

Run script with:

`python3 update.py post_id match_id`
