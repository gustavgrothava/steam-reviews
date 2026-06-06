import requests
import csv
import os
from datetime import datetime, timezone, timedelta

APP_ID = "518790"  # theHunter: Call of the Wild
CSV_FILE = "reviews.csv"
FIELDNAMES = ["date", "sentiment", "language", "review"]


def fetch_reviews():
    """Fetch all Steam reviews from yesterday using cursor-based pagination."""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_yesterday = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)

    start_ts = int(start_of_yesterday.timestamp())
    end_ts = int(end_of_yesterday.timestamp())

    reviews = []
    cursor = "*"
    page = 0

    print(f"Fetching reviews for {yesterday.strftime('%Y-%m-%d')}...")

    while True:
        page += 1
        params = {
            "json": 1,
            "filter": "recent",
            "language": "all",
            "num_per_page": 100,
            "cursor": cursor,
            "purchase_type": "all",
        }

        resp = requests.get(
            f"https://store.steampowered.com/appreviews/{APP_ID}",
            params=params,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("success") != 1:
            print("Steam API returned an error.")
            break

        batch = data.get("reviews", [])
        if not batch:
            break

        # Reviews are newest-first; stop when we go past yesterday
        past_window = False
        for r in batch:
            ts = r.get("timestamp_created", 0)
            if ts < start_ts:
                past_window = True
                break
            if start_ts <= ts <= end_ts:
                body = r.get("review", "").strip()
                if body:
                    reviews.append({
                        "date": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                        "sentiment": "positive" if r.get("voted_up") else "negative",
                        "language": r.get("language", "unknown"),
                        "review": body,
                    })

        new_cursor = data.get("cursor", "")
        if past_window or not new_cursor or new_cursor == cursor:
            break

        cursor = new_cursor
        print(f"  Page {page}: collected {len(reviews)} reviews so far...")

    return reviews


def append_to_csv(reviews):
    """Append new reviews to the CSV, creating it with a header if needed."""
    file_exists = os.path.isfile(CSV_FILE)

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(reviews)

    print(f"Saved {len(reviews)} reviews to {CSV_FILE}.")


if __name__ == "__main__":
    reviews = fetch_reviews()
    if reviews:
        append_to_csv(reviews)
    else:
        print("No reviews found for yesterday.")
