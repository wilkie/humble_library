import json
from flask import Flask, request, redirect, url_for, \
                  abort, render_template, flash

# CONFIGURATION

DEBUG = True

app = Flask("humble")
app.config.from_object(__name__)

# Load games
games_by_title = json.load(open("data/humble_list.json"))
games = list(games_by_title.keys())
games.sort()

icons_by_title = json.load(open("data/icons.json"))

steam_info_by_title = json.load(open("data/steam_info.json"))

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

    if game in steam_info_by_title:
      # Determine tags
      for tag in steam_info_by_title[game]["tags"]:
        if not tag in tags:
          tags.append(tag)
        if not tag in games_by_tag:
          games_by_tag[tag] = []
        games_by_tag[tag].append(game)


tags.sort()

@app.route("/")
def dashboard():
  return render_template('index.html', games      = pc_games,
                                       info       = games_by_title,
                                       icons      = icons_by_title,
                                       steam_info = steam_info_by_title)

@app.route("/tags/<tag>")
def tag_show(tag):
  game_list = games
  if tag in tags:
    game_list = games_by_tag[tag]

  return render_template('index.html', games      = game_list,
                                       info       = games_by_title,
                                       icons      = icons_by_title,
                                       steam_info = steam_info_by_title)

@app.route("/games/<id>")
def game_show(id):
  return 'Game %s' % id

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

if __name__ == "__main__":
  http_server = HTTPServer(WSGIContainer(app))
  http_server.listen(8003)
  IOLoop.instance().start()
  #app.run(host='0.0.0.0', port=8003)
