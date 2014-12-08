import json
import codecs
import urllib.request
import urllib.parse
import os.path
import sys
import http.cookiejar

from urllib.error import HTTPError

from bs4 import BeautifulSoup

class GOG:
  GOG_LOGIN_URL         = "https://www.gog.com/asdf"
  GOG_LOGIN_POST_URL    = "https://login.gog.com/login_check"
  GOG_USER_URL          = "https://www.gog.com/user/ajax/?a=get"
  GOG_ACCOUNT_URL       = "https://www.gog.com/account/games/shelf"
  GOG_SHELF_DETAILS_URL = "https://www.gog.com/account/ajax?a=gamesShelfDetails&g=%s"

  def __init__(self):
    # Build session opener
    cj = http.cookiejar.CookieJar()
    processor = urllib.request.HTTPCookieProcessor(cookiejar=cj)
    self.opener = urllib.request.build_opener(processor)
    self.reader = codecs.getreader('utf-8')
    self.loggedIn = False
    self.gog_info_by_title = {}

  def load(self):
    # Load games
    self.gog_info_by_title = json.load(open("data/gog_list.json"))
    self.games = list(self.gog_info_by_title.keys())
    self.games.sort()

  def readConfig(self, username=None, password=None):
    if len(sys.argv) >= 3:
      self.username = sys.argv[1]
      self.password = sys.argv[2]
    else:
      # read config.yml
      from yaml import load, dump
      try:
        from yaml import CLoader as Loader, CDumper as Dumper
      except ImportError:
        from yaml import Loader, Dumper
      config = load(open("config/config.yml", "r"))
      if "gog" in config:
        id = 0
        if not username is None:
          for account = config["gog"]:
            id += 1
            if account["username"] == username:
              break

          if id >= len(config["gog"]):
            id = 0

        self.username = config["gog"][id]["username"]
        self.password = config["gog"][id]["password"]
      else:
        print("Error: no username and password given for gog.com")
        exit(-1)

  def login(self, username=None, password=None):
    # Read configuration
    self.username = username
    self.password = password
    self.readConfig(username, password)

    # Log in

    # Pull login tokens
    try:
      r = self.opener.open(self.GOG_LOGIN_URL).read()
    except HTTPError as e:
      r = e.read()

    soup = BeautifulSoup(r)
    auth_url = soup.find('input', id="auth_url")["value"]

    soup = BeautifulSoup(self.opener.open(auth_url))
    login_token = soup.find('input', id="login__token")["value"]

    # POST login form
    soup = BeautifulSoup(self.opener.open(self.GOG_LOGIN_POST_URL, urllib.parse.urlencode({
      "login[username]": self.username,
      "login[password]": self.password,
        "login[_token]": login_token,
         "login[login]": 'Submit'
    }).encode('ascii')))

    # Retrieve user information
    user_info = json.load(self.reader(self.opener.open(self.GOG_USER_URL)))
    self.loggedIn = True

  # Create screens path
  if not os.path.exists("static/screens"):
    os.mkdir("static/screens")

  def updateList(self):
    if not self.loggedIn:
      self.login()

    # Retrieve gog games
    soup = BeautifulSoup(self.opener.open(self.GOG_ACCOUNT_URL))
    games = soup.find('div', id="shelfGamesList").find_all('div', class_='shelf_game')
    gog_games = []
    for game in games:
      if "empty" in game["class"]:
        continue

      icon_url = game.find('img', class_='shelf_game_box')["src"]

      gog_games.append({
        "id": game["data-gameid"],
        "order": game["data-orderid"],
        "icon_url": icon_url
      })

    # Make directory for gog data
    if not os.path.exists("static/screens"):
      os.mkdir("static/screens")

    if not os.path.exists("static/thumbs"):
      os.mkdir("static/thumbs")

    # Pull game information
    for game in gog_games:
      game_info = self.pullGameInfo(game)
      self.gog_info_by_title[game_info["name"]] = game_info
      print("Retrieved game %s" % (game_info["name"]))

  def writeList(self):
    o = open("data/gog_list.json", "w+")
    o.write(json.dumps(self.gog_info_by_title))
    o.close()

  def pullGameInfo(self, game):
    various_info = json.load(self.reader(self.opener.open(self.GOG_SHELF_DETAILS_URL % (game['id']))))
    status = various_info.get('result') or ''
    if status != "ok":
      return None

    # Parse game html
    soup = BeautifulSoup(various_info["details"]["html"])
    shelf_det_top = soup.find('div', class_='shelf_det_top')
    header = shelf_det_top.find('h2')
    game_link = header.find('a')
    game_name = game_link.get_text().strip()
    game_url  = game_link["href"]

    hash = {
      "provider":  "gog",
      "username":  self.username,
      "name":      game_name,
      "url":       game_url,
      "downloads": [],
      "screens":   [],
      "tags":      []
    }

    # Get filename of icon from url
    url = game["icon_url"]

    # Pull game icon
    filename = url[url.rindex('/')+1:]
    if not os.path.exists("static/icons/%s" % (filename)):
      try:
        print("Pulling %s for %s" % (filename, game_name))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Pulling %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))
      try:
        urllib.request.urlretrieve(url, "static/icons/%s" % (filename))
        icon_url = filename
      except:
        icon_url = "default.png"
        print("404")
    else:
      try:
        print("Exists: %s for %s" % (filename, game_name))
      except:
        # Argh. Sometimes it hates the encoding when it tries to print on
        # some terminals. Freaking python.
        print("Exists: %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))
      icon_url = filename

    hash["icon"] = filename

    # Pull out downloads
    platforms = [['windows', 'win-download'], ['mac', 'mac-download'], ['linux', 'linux-download']]

    for platform, class_id in platforms:
      download_container = soup.find('div', class_='list_down_browser').find('div', class_=class_id)
      if download_container is None:
        continue

      print("found downloads for %s" % (platform))

      platform_download = {
        "options": [],
        "platform": platform
      }

      print(download_container)
      downloads = download_container.find_all('a', class_='list_game_item')
      for download in downloads:
        download_url = download["href"]
        download_version = download.find('span', class_='version').get_text().strip()
        download_filesize = download.find('span', class_='size').get_text().strip()
        download_name = download.find('span', class_='details-underline').get_text().strip()
        platform_download["options"].append({
          "version": download_version,
          "url": download_url,
          "file_size": download_filesize,
          "name": download_name
        })

      hash["downloads"].append(platform_download)

    # Pull screens
    soup = BeautifulSoup(self.opener.open(game_url))
    thumbs = soup.find_all('img', class_='screen-tmb__img')
    for thumb in thumbs:
      screen_url = thumb["src"]

      parts = urllib.parse.urlparse(screen_url)
      shorturl = parts.path
      filename = shorturl[shorturl.rindex('/')+1:]

      if not os.path.exists("static/screens/%s" % game['id']):
        os.mkdir("static/screens/%s" % game['id'])

      if not os.path.exists("static/thumbs/%s" % game['id']):
        os.mkdir("static/thumbs/%s" % game['id'])

      if not os.path.exists("static/screens/%s/%s" % (game['id'], filename)):
        try:
          print("Pulling %s for %s" % (filename, game_name))
        except:
          # Argh. Sometimes it hates the encoding when it tries to print on
          # some terminals. Freaking python.
          print("Pulling %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))
        try:
          urllib.request.urlretrieve(screen_url, "static/screens/%s/%s" % (game['id'], filename))
        except:
          print("404")
      else:
        try:
          print("Exists: %s for %s" % (filename, game_name))
        except:
          # Argh. Sometimes it hates the encoding when it tries to print on
          # some terminals. Freaking python.
          print("Exists: %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))

      if not os.path.exists("static/thumbs/%s/%s" % (game['id'], filename)):
        try:
          print("Pulling %s for %s" % (filename, game_name))
        except:
          # Argh. Sometimes it hates the encoding when it tries to print on
          # some terminals. Freaking python.
          print("Pulling %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))
        try:
          urllib.request.urlretrieve(screen_url, "static/thumbs/%s/%s" % (game['id'], filename))
        except:
          print("404")
      else:
        try:
          print("Exists: %s for %s" % (filename, game_name))
        except:
          # Argh. Sometimes it hates the encoding when it tries to print on
          # some terminals. Freaking python.
          print("Exists: %s for %s" % (filename, game_name.encode('ascii', 'ignore').decode('ascii')))

      hash["screens"].append({
        "thumb": "%s/%s" % (game["id"], filename),
        "id": filename,
        "screens": "%s/%s" % (game["id"], filename)
      })

    # Pull description
    description = soup.find('div', class_='description__text', attrs={"ng-show": "showAll"})
    if description is None:
      description = soup.find('div', class_='description__text')

    hash["description"] = description.get_text().strip()

    # Pull tags
    tags = soup.find('div', class_='product-details__data').find_all('a', class_='un')
    for tag in tags:
      tag = tag.get_text().strip()

      # Reform tags
      if tag == "Point-and-click":
        tag = "Point & Click"

      hash["tags"].append(tag)


    # Add game ids to hash
    hash.update(game)

    # Return game info hash
    return hash
