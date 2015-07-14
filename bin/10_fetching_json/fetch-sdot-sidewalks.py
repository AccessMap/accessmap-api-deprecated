import datetime
import json
import requests


SOCRATA_KEY = "HyursDSMdzrAfLroxKO1rztA5"

params = {"$limit": 50000}

r = requests.get("https://data.seattle.gov/resource/pxgh-b4sz.json",
                 params=params,
                 headers={"X-App-Token": SOCRATA_KEY})


today = datetime.date.today().isoformat()
with open("./sidewalk-sdot-{}.json".format(today), "w") as f:
    json.dump(r.json(), f)


with open("./sidewalk-sdot-latest.json", "w") as f:
    json.dump(r.json(), f)
