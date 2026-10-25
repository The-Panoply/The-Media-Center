#!/usr/bin/env python3
"""Resolve missing TMDb posters into the public watchlist catalog."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

path = Path("catalog.json")
catalog = json.loads(path.read_text(encoding="utf-8"))
token = os.environ["TMDB_API_TOKEN"]
headers = {"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "The-Media-Center/1.0"}

def api(endpoint, params):
    url = "https://api.themoviedb.org/3/" + endpoint + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def norm(value):
    return "".join(ch for ch in value.casefold() if ch.isalnum())

def resolve(item):
    title = item["title"]
    year = int(item["year"])
    tv = item.get("type") == "TV"
    endpoint = "search/tv" if tv else "search/movie"
    key = "first_air_date" if tv else "release_date"
    label = "name" if tv else "title"
    data = api(endpoint, {"query": title, "include_adult": "false", "language": "en-US"})
    candidates = []
    for result in data.get("results", []):
        if not result.get("poster_path") or norm(result.get(label, "")) != norm(title):
            continue
        release = result.get(key, "")
        if not release or not release[:4].isdigit():
            continue
        delta = abs(int(release[:4]) - year)
        if delta <= 1:
            candidates.append((delta, -result.get("popularity", 0), result))
    if not candidates:
        return None
    result = min(candidates)[2]
    return {"poster": "https://image.tmdb.org/t/p/w500" + result["poster_path"], "tmdb_id": result["id"]}

changed = 0
unresolved = []
for section, items in catalog["lists"].items():
    for item in items:
        if item.get("poster"):
            continue
        try:
            match = resolve(item)
            if match:
                item.update(match)
                changed += 1
                print("MATCH", section, item["title"], item["year"], item["tmdb_id"])
            else:
                unresolved.append(item["title"] + " (" + str(item["year"]) + ")")
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            print("LOOKUP ERROR", item["title"], str(exc))
            unresolved.append(item["title"] + " (" + str(item["year"]) + ")")
        time.sleep(0.15)
if changed:
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("Resolved:", changed, "Unresolved:", len(unresolved))
for name in unresolved:
    print("UNRESOLVED", name)
