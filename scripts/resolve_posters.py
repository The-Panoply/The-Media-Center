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

def details(item):
    kind = "tv" if item.get("type") == "TV" else "movie"
    data = api(kind + "/" + str(item["tmdb_id"]), {"language": "en-US"})
    runtimes = data.get("episode_run_time", []) if kind == "tv" else [data.get("runtime")]
    runtime = next((v for v in runtimes if isinstance(v, int) and v > 0), None)
    rating = data.get("vote_average")
    try:
        credits = api(kind + "/" + str(item["tmdb_id"]) + "/credits", {"language": "en-US"})
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print("CREDITS ERROR", item["title"], str(exc))
        credits = {}
    try:
        providers = api(kind + "/" + str(item["tmdb_id"]) + "/watch/providers", {})
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print("PROVIDERS ERROR", item["title"], str(exc))
        providers = {}
    us = providers.get("results", {}).get("US", {})
    streaming = [p["provider_name"] for p in us.get("flatrate", []) if p.get("provider_name")]
    rent = [p["provider_name"] for p in us.get("rent", []) if p.get("provider_name")]
    buy = [p["provider_name"] for p in us.get("buy", []) if p.get("provider_name")]
    def logo_items(kind):
        seen = set()
        result = []
        for provider in us.get(kind, []):
            name = provider.get("provider_name")
            logo = provider.get("logo_path")
            if name and logo and name not in seen:
                result.append({"name": name, "logo": "https://image.tmdb.org/t/p/w92" + logo})
                seen.add(name)
        return result
    return {
        "cast": [p["name"] for p in credits.get("cast", []) if p.get("name")][:4] or item.get("cast", []),
        "poster": ("https://image.tmdb.org/t/p/w500" + data["poster_path"]) if data.get("poster_path") else item.get("poster"),
        "watch_us": {"stream": list(dict.fromkeys(streaming)), "rent": list(dict.fromkeys(rent)), "buy": list(dict.fromkeys(buy)), "stream_logos": logo_items("flatrate"), "rent_logos": logo_items("rent"), "buy_logos": logo_items("buy"), "source": "TMDb", "checked": time.strftime("%Y-%m-%d")},
        "synopsis": data.get("overview") or None,
        "genres": [g["name"] for g in data.get("genres", []) if g.get("name")][:3],
        "runtime_minutes": runtime,
        "tmdb_rating": round(rating, 1) if isinstance(rating, (int, float)) and data.get("vote_count", 0) else None,
        "imdb_id": data.get("imdb_id") if kind == "movie" else None,
    }

changed = 0
unresolved = []
for section, items in catalog["lists"].items():
    for item in items:
        if item.get("tmdb_id") and item.get("synopsis") and "genres" in item and "tmdb_rating" in item and "cast" in item and "watch_us" in item and "stream_logos" in item["watch_us"]:
            continue
        try:
            match = None if item.get("tmdb_id") else resolve(item)
            if match:
                item.update(match)
            if item.get("tmdb_id"):
                metadata = details(item)
                if any(item.get(k) != v for k, v in metadata.items()) or match:
                    item.update(metadata)
                    changed += 1
                print("METADATA", section, item["title"], item["year"])
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
