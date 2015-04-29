import datetime
import json
import requests


SOCRATA_KEY = "HyursDSMdzrAfLroxKO1rztA5"

params = {"$where": "sidewalk_close_end_date > '2015-04-28'",
          "sidewalk_closed_flag": "Y",
          "$limit": 50000}

# r = requests.get("https://data.seattle.gov/resource/czy3-hkh9",
r = requests.get("https://data.seattle.gov/resource/w47m-dg37",
                 params=params,
                 headers={"X-App-Token": SOCRATA_KEY})

try:
    if "message" in r.json():
        print r.json()["message"]
except:
    pass

json_list = r.json()

today = datetime.date.today().isoformat()
with open("./permits-by-street-segment-{}.json".format(today), "w") as f:
    json.dump(json_list, f)


with open("./permits-by-street-segment-latest.json", "w") as f:
    json.dump(json_list, f)
