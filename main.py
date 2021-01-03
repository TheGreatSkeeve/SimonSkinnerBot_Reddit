import os
from time import sleep
import praw
import sqlite3
from pathlib import Path
import datetime


dbname = "SimonSkinnerBot.db"
dbfolder = "db/"
sanford_dict = {}

keyword = "the greater good"
comments_me_count = 0
comments_processed_count = 0
goodbot_count = 0
badbot_count = 0
deleted_count = 0

# This makes the database folder if it doesn't exist
Path(dbfolder).mkdir(parents=True, exist_ok=True)

# Telegram
token = ""
chatid = ""

# Reddit
target_sub = "all"  # Where the bot looks for the words
bot_username = ["SimonSkinnerBot", "B0tRank"]  # Bot's username, because I'm too lazy to pull it from reddit.
rating_report = ["Time: ", "Comment ID", "Comment Body", "Comment Link", "Parent ID", "Parent Body", "Parent Link"]

# Responses
bot_feedback = [
    ['good bot', 'Yes, thank you!'],
    ['bad bot', '[Sorry about that.  I\'ve logged your review.  Please DM u/TheGreatSkeeve_ if you have any further feedback to provide]']
]
bot_response = [
        ">",
        "",
        "\n\n[The Greater Good.](https://www.reddit.com/r/hotfuzz)",
        "\n\n^(I'm) ^(a) ^(bot)^(,) ",
        "^(please) ^(message) [^(u/thegreatskeeve_)](https://www.reddit.com/user/thegreatskeeve_) ^(for) ^(comments) ^(or) ^(complaints)"
]

# Admin
data_file = ["comment_list.txt", "bot_ratings.txt"]  # Persistant storage
consoleoutput = ["\nI'm here to slash prices and throats, and I'm all out of prices!\n", "Ignoring comments from the bot rater...", "Thanking a voter!",
                 "Apoligizing and deleting...whoops.",]

# Sign into Reddit
reddit = praw.Reddit(
    client_id="",
    client_secret="",
    password="",
    user_agent="",
    username=""
)

# Set the target sub (r/all)
subreddit = reddit.subreddit(target_sub)  # Making the code look prettier.

#date   How many comments I've made     how many comments I've processed        How many good bots      How many bad bots       How many deleted comments
def init_sqlite():
    conn = sqlite3.connect(dbfolder + dbname)
    c = conn.cursor()
    c.execute('''CREATE TABLE stats (date date, Comments_Made int, Comments_Read int, Good_Bot int, Bad_Bot int, Deleted int)''')

def sqlite_connect():
    global conn
    conn = sqlite3.connect(dbfolder + dbname, check_same_thread=False)

def sqlite_load_all():
    sqlite_connect()
    c = conn.cursor()
    c.execute('SELECT * FROM stats ORDER BY date DESC LIMIT 1')
    rows = c.fetchall()
    conn.close()
    return rows

def sanford_load():
    global comments_me_count
    global comments_processed_count
    global goodbot_count
    global badbot_count
    global deleted_count
    global sanford_dict
    if bool(sanford_dict):
        sanford_dict.clear()
    for row in sqlite_load_all():
        sanford_dict=(row[0],row[1], row[2], row[3], row[4],row[5])
    comments_me_count = sanford_dict[1]
    comments_processed_count = sanford_dict[2]
    goodbot_count = sanford_dict[3]
    badbot_count = sanford_dict[4]
    deleted_count = sanford_dict[5]


def sqlite_write(comments_made,comments_read,good,bad,deleted):
    sqlite_connect()
    c = conn.cursor()
    x = datetime.datetime.now()
    q = [(x), (comments_made), (comments_read), (good), (bad), (deleted)]
    c.execute('''INSERT INTO stats('date','Comments_Made','Comments_Read','Good_Bot','Bad_Bot','Deleted') VALUES(?,?,?,?,?,?)''', q)
    conn.commit()
    conn.close()

# Function to send a message to THC-Development group in Telegram
def sendMessage(message):
    import requests
    msg1 = "https://api.telegram.org/bot"
    msg2 = "/sendMessage?chat_id="
    msg3 = "&text="
    URL = msg1+token+msg2+chatid+msg3+message
    r = requests.get(url=URL)

# Function to respond if we're rate-limited
# This doesn't happen much, will probably delete
def rateLimit(error,comment):
    timeleft = ((error.split("try again in "))[1].split(" minute"))[0]
    part_1 = "We're being rate-limited...stupid Reddit."
    part_2 = error
    part_3 = "Sleeping for " + timeleft + " minutes until I can comment again..."
    link = "(" + str(comment.permalink) + ")"
    outOfJail = "Okay, ratelimit should be over"
    message = part_1 + "\n" + link + "\n" + part_2 + "\n" + part_3
    sendMessage(message)
    sendMessage(link)
    sleep((int(timeleft) * 60) + 1)
    sendMessage(outOfJail)

# Function to delete the comment if we get a "Bad Bot" rating
def badBot(comment):
    global badbot_count
    comment_parent = comment.parent()
    parent_author = str(comment_parent.author)
    if parent_author == "SimonSkinnerBot":
        badbot_count += 1
        sendMessage("Bad Bot Alert - Bad Bot Alert")
        sendMessage(comment.permalink)
        sendMessage("Bad Bot Alert - Bad Bot Alert")
        if comment_parent.score < 10:
            comment_parent.delete()
    sqlite_write(comments_me_count, comments_processed_count, goodbot_count, badbot_count, deleted_count)

def findSubString(comment,text):
    numstart = comment.index(text)
    numend = numstart + 16
    replytext = comment[numstart:numend]
    return replytext

def healthCheckerPing():
    import requests
    url = "https://hc-ping.com/86d42e5c-5ec3-4e48-89f0-9e9a7c2834b6"
    requests.get(url)

# Let Telegram know we're running
sendMessage("Simon Skinner is powering up")
# Let the console know we're running
print(consoleoutput[0])
# Count the comments

try:
    init_sqlite()
except sqlite3.OperationalError:
    pass

sanford_load()

# Runs for the last 100 comments / any new comments
for comment in subreddit.stream.comments():
    healthCheckerPing()
    # Add it to the count of comments we've read
    comments_processed_count += 1
    # Make the comment all lower case
    comment_body = comment.body.lower()
    # Catch if it's a "bad bot" rating
    if "bad bot" in comment_body:
        badBot(comment)
    # Don't get caught in a Greater Good loop.
    if comment.author == bot_username[0]:
        comment_body="Fuck off"
    # Someone said "The Greater Good", time to chime in.
    if keyword in comment_body:
        # Set the precise case of the original "The Greater Good"
        bot_response[1] = findSubString(comment_body,keyword)
        # Alert Telegram that we're making a comment
        sendMessage(str(comment.author) + "\n" + comment_body + "\nhttps://reddit.com" + str(comment.permalink) + "\n")
        # Try and make the comment
        try:
            comment.reply(bot_response[0]+bot_response[1]+bot_response[2]+bot_response[3]+bot_response[4])
            comments_me_count += 1
        except Exception as e:
            print("Probably rate-limited again.\n"+e)
        # Try and update SQL
        try:
            sqlite_write(comments_me_count, comments_processed_count, goodbot_count, badbot_count, deleted_count)
        except Exception as e:
            sendMessage("Caught an exception writing to SQL.\n"+str(e))
