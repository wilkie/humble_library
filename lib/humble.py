import json
import sys
import os
from humblebundle import HumbleApi

import urllib.request
import urllib.parse
from urllib.error import HTTPError

# Create a data directory if it doesn't exist
if not os.path.exists("./data"):
  os.mkdir("./data")

# Log on to HumbleBundle
client = HumbleApi()

if len(sys.argv) >= 3:
  username = sys.argv[1]
  password = sys.argv[2]
else:
  # read config.yml
  from yaml import load, dump
  try:
    from yaml import CLoader as Loader, CDumper as Dumper
  except ImportError:
    from yaml import Loader, Dumper
  config = load(open("config/config.yml", "r"))
  username = config["humblebundle"]["username"]
  password = config["humblebundle"]["password"]

print("Logging in as %s" % (username))
client.login(username, password)

# Grab gamekeys
gamekeys = client.get_gamekeys()

games_by_title = {}
games = []

def load_games():
  for gamekey in gamekeys:
    order = client.get_order(gamekey)
    if not order is None and not order.subproducts is None:
      for subproduct in order.subproducts:
        game_name = subproduct.human_name
        if game_name is None:
          game_name = subproduct.machine_name
        game_name = game_name.strip()
        if not game_name in games_by_title:
          data = {
            "provider": "humble",
            "order": gamekey,
            "url": (subproduct.url or "").strip(),
            "name": (subproduct.human_name or "").strip(),
            "id": (subproduct.machine_name or "").strip(),
            "icon_url": (subproduct.icon or "").strip(),
            "downloads": [
              {"platform": (download.platform or "").strip(),
               "options":  [{
                 "url":      (option.url.web or "").strip(),
                 "name":     (option.name or "").strip(),
                 "md5":      (option.md5 or "").strip(),
                 "file_size":(option.file_size or 0),
                 "size":     (option.size or 0),
                 "message":  (option.message or "").strip(),
                 "sha1":     (option.sha1 or "").strip()
               } for option in download.download_struct],
               "id": download.download_identifier,
               "version": download.download_version_number
            } for download in subproduct.downloads],
            "payee": subproduct.payee.human_name
          }
          if not len(data["downloads"]) == 0:
            # Get filename from url
            url = data["icon_url"]

            filename = "%s-%s" % (data['order'], url[url.rindex('/')+1:])
            if not os.path.exists("static/icons/%s" % (filename)):
              try:
                print("Pulling %s for %s" % (filename, data['name']))
              except:
                # Argh. Sometimes it hates the encoding when it tries to print on
                # some terminals. Freaking python.
                print("Pulling %s for %s" % (filename, data['name'].encode('ascii', 'ignore').decode('ascii')))
              try:
                urllib.request.urlretrieve(url, "static/icons/%s" % (filename))
                data['icon'] = filename
              except:
                print("404")
                data['icon'] = 'default.png'
            else:
              print("Exists: %s for %s" % (filename, data['name']))
              data['icon'] = filename

            games_by_title[game_name] = data
            games.append(data)
            try:
              print(subproduct.human_name)
            except:
              # Argh. Sometimes it hates the encoding when it tries to print on
              # some terminals. Freaking python.
              print(subproduct.human_name.encode('ascii', 'ignore').decode('ascii'))


load_games()

o = open("data/humble_list.json", "w+")
o.write(json.dumps(games_by_title))
o.close()
