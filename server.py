import json
from flask import Flask, request, redirect, url_for, \
                  abort, render_template, flash

from humblebundle import HumbleApi
from lib.gog import GOG

# CONFIGURATION

DEBUG = True

app = Flask("humble")
app.config.from_object(__name__)

# Load games
humble_games = json.load(open("data/humble_list.json"))
gog_games    = json.load(open("data/gog_list.json"))

games_by_title = {}
games_by_title.update(humble_games)
games_by_title.update(gog_games)

games = list(games_by_title.keys())
games.sort()

steam_info_by_title = json.load(open("data/steam_info.json"))

# Combine steam info into normal game info
for game_name, game_info in steam_info_by_title.items():
  if game_name in games_by_title:
    games_by_title[game_name].update(game_info)

pc_games = []
audio = []
books = []

# Load tags
tags = []
games_by_tag = {}

# Sort into platforms and tags etc
platforms = {}
for game in games:
  info = games_by_title[game]
  avail_platforms = set([option["platform"] for option in info["downloads"]])

  for platform in avail_platforms:
    if not platform in platforms:
      platforms[platform] = []
    platforms[platform].append(game)
  if "audio" in avail_platforms:
    audio.append(game)
  if "ebook" in avail_platforms:
    books.append(game)
  if "windows" in avail_platforms or "mac" in avail_platforms or "linux" in avail_platforms:
    pc_games.append(game)

    if game in games_by_title:
      # Determine tags
      if 'tags' in games_by_title[game]:
        for tag in games_by_title[game]["tags"]:
          if not tag in tags:
            tags.append(tag)
          if not tag in games_by_tag:
            games_by_tag[tag] = []
          games_by_tag[tag].append(game)


tags.sort()

@app.route("/")
def dashboard():
  # Get random 10 games

  games = pc_games
  if len(pc_games) > 10:
    games = pc_games[0:10]

  return render_template('index.html', games = pc_games[0:10],
                                       info  = games_by_title)

@app.route("/tags/<tag>")
def tag_show(tag):
  game_list = games
  if tag in tags:
    game_list = games_by_tag[tag]

  return render_template('index.html', games = game_list,
                                       info  = games_by_title)

@app.route("/games/<id>")
def game_show(id):
  return 'Game %s' % id

@app.route("/downloads/<game>/<platform>")
def download_game(game, platform):
  # Look up order key and game key
  game = games_by_title.get(game)

  if game is None:
    return 404

  provider = game["provider"]

  if provider == "humble":
    gamekey = game["order"]
    id      = game["id"]

    # Log on to HumbleBundle
    client = HumbleApi()

    # read config.yml
    from yaml import load, dump
    try:
      from yaml import CLoader as Loader, CDumper as Dumper
    except ImportError:
      from yaml import Loader, Dumper
    config = load(open("config/config.yml", "r"))
    username = config["humblebundle"]["username"]
    password = config["humblebundle"]["password"]

    client.login(username, password)

    order = client.get_order(gamekey)
    if not order is None and not order.subproducts is None:
      for subproduct in order.subproducts:
        if subproduct.machine_name == id:
          # This game. Look through downloads for the right platform.
          for download in subproduct.downloads:
            if download.platform == platform:
              return redirect(download.download_struct[0].url.web, code=302)
  elif provider == "gog":
    # Log on to gog.com
    # Retrieve download link for this download option
    gog = GOG()
    gog.login(game["username"])
    info = gog.pullGameInfo(game)
    for download in info["downloads"]:
      if download["platform"] == platform:
        return redirect(download["options"][0]["url"], code=302)

  return 404

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

if __name__ == "__main__":
  #http_server = HTTPServer(WSGIContainer(app))
  #http_server.listen(8082, '0.0.0.0')
  #IOLoop.instance().start()
  app.run(host='0.0.0.0', port=9292)
