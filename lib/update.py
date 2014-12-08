from gog import GOG

gog = GOG()
print("Logging in")
gog.login()
print("Pulling Existing List")
gog.load()
print("Retrieving List")
gog.updateList()
print("Writing List")
gog.writeList()
print("Done")
