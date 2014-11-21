import json
import urllib.request
import os.path

# Load games
games_by_title = json.load(open("data/humble_list.json"))

icons_by_title = {}

# Pull icons (if needed)
for game, info in games_by_title.items():
  # Get filename from url
  url = info["icon_url"]

  filename = url[url.rindex('/')+1:]
  if not os.path.exists("static/icons/%s" % (filename)):
    print("Pulling %s for %s" % (filename, game))
    try:
      urllib.request.urlretrieve(url, "static/icons/%s" % (filename))
      icons_by_title[game] = filename
    except:
      print("404")
      icons_by_title[game] = "default.png"
  else:
    print("Exists: %s for %s" % (filename, game))
    icons_by_title[game] = filename

o = open("data/icons.json", "w+")
o.write(json.dumps(icons_by_title))
o.close()
