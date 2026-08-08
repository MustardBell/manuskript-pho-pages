"""What this plugin calls itself when it talks to the host.

One fact, in one place, because three modules now depend on it agreeing:
the page type is registered under this ID, its settings panel asks the host
for that ID's export routing, and its reading view names it when converting
so that an addition written for PHO pages applies there. Two of the three
had no business owning it for the others.
"""

#: The page type PHO registers. Also the key its renderer routing is stored
#: under, so it is not free to change.
PAGE_TYPE_ID = "manuskript.pho-page"
