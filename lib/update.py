import json
import sys
from humblebundle import HumbleApi

# Log on to HumbleBundle
client = HumbleApi()

# TODO: add config
client.login(sys.argv[1], sys.argv[2])

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
            games_by_title[game_name] = data
            games.append(data)
            print(subproduct.human_name)

load_games()

o = open("data/humble_list.json", "w+")
o.write(json.dumps(games_by_title))
o.close()
