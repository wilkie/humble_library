# Patch HTTP for incomplete reads (because that is a thing, apparently)
import http.client

def patch_http_response_read(func):
  def inner(*args):
    try:
      return func(*args)
    except(httplib.IncompleteRead, e):
      return e.partial

  return inner

http.client.HTTPResponse.read = patch_http_response_read(http.client.HTTPResponse.read)

import json
import urllib.request
import urllib.parse
import os.path
import http.cookiejar

from bs4 import BeautifulSoup

STEAM_SEARCH_URL = "http://store.steampowered.com/search/?"
STEAM_GAME_URL = "http://store.steampowered.com/app/"
STEAM_TAG_SELECTOR = "div.popular_tags a.app_tag"
STEAM_AGECHECK_URL = "http://store.steampowered.com/agecheck/app/"

# Create screens path
if not os.path.exists("static/screens"):
  os.mkdir("static/screens")

# Load games
games_by_title = json.load(open("data/humble_list.json"))
games = list(games_by_title.keys())
games.sort()

pc_games = []

# Build session opener
cj = http.cookiejar.CookieJar()
processor = urllib.request.HTTPCookieProcessor(cookiejar=cj)
opener = urllib.request.build_opener(processor)

# Sort into platforms and tags etc
platforms = {}
for game in games:
  info = games_by_title[game]
  avail_platforms = set([option["platform"] for option in info["downloads"]])
  for platform in avail_platforms:
    if not platform in platforms:
      platforms[platform] = []
    platforms[platform].append(game)
  if "windows" in avail_platforms or "mac" in avail_platforms or "linux" in avail_platforms:
    pc_games.append(game)

# Load old steam ids
steam_info_by_title = {}
if os.path.exists("data/steam_ids.json"):
  steam_info_by_title = json.load(open("data/steam_ids.json"))

# Pull steam ids (if needed)
for game in pc_games:
  info = games_by_title[game]

  # Form steam search url
  url = "%s%s" % (STEAM_SEARCH_URL, urllib.parse.urlencode({'term': game}))
  print("Getting %s" % (url))

  soup = BeautifulSoup(opener.open(url))

  # Pull that url and determine the app id from the first results

  # Look at the closest search result
  results = soup.find(id="search_result_container")
  if results is None:
    try:
      print("Cannot find %s on Steam" % (game))
    except:
      # Argh. Sometimes it hates the encoding when it tries to print on
      # some terminals. Freaking python.
      print("Cannot find %s on Steam" % (game.encode('ascii', 'ignore').decode('ascii')))
    continue

  links = results.find_all('a', class_="search_result_row")
  if links is None:
    try:
      print("Cannot find %s on Steam" % (game))
    except:
      # Argh. Sometimes it hates the encoding when it tries to print on
      # some terminals. Freaking python.
      print("Cannot find %s on Steam" % (game.encode('ascii', 'ignore').decode('ascii')))
    continue

  result_rows = [{"name":  result.find('span', class_="title").get_text().strip(),
                  "appid": result["data-ds-appid"]} for result in links]

  # Find a result with the best fitting name
  best_row = None
  best_score = 1000
  for row in result_rows:
    if row["name"].lower() == game.lower():
      best_row = row
      best_score = 0
      break

    if len(game) > 7 and row["name"].lower().startswith(game[:7].lower()):
      score = abs(len(row["name"]) - len(game))
      if score < best_score:
        best_row = row
        best_score = score

  if best_row is None:
    try:
      print("Cannot find %s on Steam" % (game))
    except:
      # Argh. Sometimes it hates the encoding when it tries to print on
      # some terminals. Freaking python.
      print("Cannot find %s on Steam" % (game.encode('ascii', 'ignore').decode('ascii')))
    continue

  appid = best_row["appid"]
  name  = best_row["name"]

  if not game in steam_info_by_title:
    steam_info_by_title[game] = {}

  steam_info_by_title[game]["appid"] = appid

  # Go to the application page
  url = "%s%s" % (STEAM_GAME_URL, appid)
  print("Getting %s" % (url))

  soup = BeautifulSoup(opener.open(url))

  # Check for "enter a birthday" bullshit
  birthdayYear = soup.find('select', id='ageYear')
  if not birthdayYear is None:
    print("Saying I'm a fucking adult")
    # Enter in a birthday, year 1970 why not
    birthday_post_url = "%s/%s" % (STEAM_AGECHECK_URL, appid)

    # Get 'snr' token
    snr = soup.find('form', id='agecheck_form').find('input', attrs={"name": "snr"})["value"]
    soup = BeautifulSoup(opener.open(birthday_post_url, urllib.parse.urlencode({"ageDay": "1", "ageMonth": "January", "ageYear": "1970", "snr": snr}).encode('ascii')))

  steam_info_by_title[game]["name"] = name
  try:
    print("Steam Name: %s" % (name))
  except:
    # Argh. Sometimes it hates the encoding when it tries to print on
    # some terminals. Freaking python.
    print("Steam Name: %s" % (name.encode('ascii', 'ignore').decode('ascii')))

  # Pull out tags
  def is_tag(tag):
    return tag.name == "a" and tag.has_attr("class") and tag["class"] == ["app_tag"]

  tags = soup.find_all(is_tag)
  steam_info_by_title[game]["tags"] = [tag.get_text().strip() for tag in tags]

  # Pull out description
  try:
    html_description = '\n'.join(soup.find(id='game_area_description').prettify().split('\n')[4:-2]).replace("</br>", "").replace("<br/>", "")
  except:
    html_description = ""

  steam_info_by_title[game]["description"] = html_description

  # Pull out screenshots
  def is_screen(tag):
    return tag.name == "div" and tag.has_attr("class") and "highlight_strip_item" in tag["class"] and "highlight_strip_screenshot" in tag["class"]

  screens = soup.find_all(is_screen)
  screen_urls = [{"url": screen.find('img')["src"], "id": screen["id"][len("thumb_screenshot_"):]} for screen in screens]

  # Make directory for steam data
  if not os.path.exists("static/screens"):
    os.mkdir("static/screens")

  if not os.path.exists("static/screens/%s" % appid):
    os.mkdir("static/screens/%s" % appid)

  if not os.path.exists("static/thumbs"):
    os.mkdir("static/thumbs")

  if not os.path.exists("static/thumbs/%s" % appid):
    os.mkdir("static/thumbs/%s" % appid)

  steam_info_by_title[game]["screens"] = []

  for screen_url in screen_urls:
    screen_id = screen_url["id"]
    thumb_url = screen_url["url"]
    screen_url = screen_id

    parts = urllib.parse.urlparse(thumb_url)
    shorturl = parts.path
    filename = shorturl[shorturl.rindex('/')+1:]

    screen_info = {}
    screen_info["id"] = screen_id

    screen_base_url = thumb_url[:thumb_url.rindex(filename)]
    screen_ext = filename[filename.rindex('.'):]

    screen_url = "%s%s.600x338%s" % (screen_base_url, screen_id[:-len(screen_ext)], screen_ext)

    if not os.path.exists("static/screens/%s/%s" % (appid, filename)):
      try:
        print("Pulling %s for %s" % (filename, game))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Pulling %s for %s" % (filename, game.encode('ascii', 'ignore').decode('ascii')))
      try:
        urllib.request.urlretrieve(screen_url, "static/screens/%s/%s" % (appid, filename))
        screen_info["screens"] = "%s/%s" % (appid, filename)
      except:
        print("404")
    else:
      try:
        print("Exists: %s for %s" % (filename, game))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Exists: %s for %s" % (filename, game.encode('ascii', 'ignore').decode('ascii')))
      screen_info["screens"] = "%s/%s" % (appid, filename)

    if not os.path.exists("static/thumbs/%s/%s" % (appid, filename)):
      try:
        print("Pulling %s for %s" % (filename, game))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Pulling %s for %s" % (filename, game.encode('ascii', 'ignore').decode('ascii')))
      try:
        urllib.request.urlretrieve(thumb_url, "static/thumbs/%s/%s" % (appid, filename))
        screen_info["thumb"] = "%s/%s" % (appid, filename)
      except:
        print("404")
    else:
      try:
        print("Exists: %s for %s" % (filename, game))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Exists: %s for %s" % (filename, game.encode('ascii', 'ignore').decode('ascii')))
      screen_info["thumb"] = "%s/%s" % (appid, filename)

    steam_info_by_title[game]["screens"].append(screen_info)

o = open("data/steam_info.json", "w+")
o.write(json.dumps(steam_info_by_title))
o.close()
