#! /usr/bin/env python3

from bs4 import BeautifulSoup
import requests
import argparse
from datetime import datetime, timezone
import sqlite3
import xml.etree.ElementTree as ET
from uuid import uuid4


def get_entries(scraping_url: str):
    db = sqlite3.connect("feed.db")
    db.execute("CREATE TABLE IF NOT EXISTS lnt_feed(id, title, url, date);")
    html = requests.get(scraping_url).text
    soup = BeautifulSoup(html, "html.parser")
    latest_updates = soup.find(class_="latest-updates")
    for entry_row in latest_updates.find_all(class_="content_list_latest-wrap-item"):
        # Create title by combining name of story and name of chapter.
        story_title = entry_row.find(title="Title").a.string
        chapter = entry_row.find(title="Releases").a.string
        entry_title = f"{story_title} | {chapter}"
        entry_url = entry_row.find(title="Releases").a["href"]
        record = db.execute(
            "SELECT id, date FROM lnt_feed WHERE url = ?;", [entry_url]
        ).fetchone()
        if not record:
            entry_id = uuid4().urn
            entry_date = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
            db.execute(
                "INSERT INTO lnt_feed VALUES(?, ?, ?, ?);",
                (entry_id, entry_title, entry_url, entry_date),
            )
            db.commit()
        else:
            entry_id = record[0]
            entry_date = record[1]
        yield {
            "id": entry_id,
            "title": entry_title,
            "url": entry_url,
            "date": entry_date,
        }


def generate_feed(feed_path: str, scraping_url: str):
    # Build XML atom feed.
    feed = ET.Element("feed", {"xmlns": "http://www.w3.org/2005/Atom"})
    ET.SubElement(feed, "title").text = "Light Novel Translations"
    ET.SubElement(
        feed,
        "link",
        {
            "href": "https://vega.frost.cx/feed/lightnoveltranslations.atom",
            "rel": "self",
        },
    )
    ET.SubElement(feed, "updated").text = datetime.now(tz=timezone.utc).isoformat(
        timespec="seconds"
    )
    ET.SubElement(feed, "id").text = "urn:uuid:32387ba5-5728-4632-80d2-e144b5217e57"
    author = ET.SubElement(feed, "author")
    ET.SubElement(author, "name").text = "Light Novel Translations"
    ET.SubElement(author, "uri").text = "https://lightnovelstranslations.com/"
    ET.SubElement(
        feed, "icon"
    ).text = "https://i0.wp.com/lightnovelstranslations.com/wp-content/uploads/2020/12/cropped-favicon-32px.png"
    ET.SubElement(
        feed, "generator", {"uri": "https://github.com/Fraetor/LNT_feed_generator"}
    ).text = "Horrible hand-coded feed generator"

    # Loop to generate and add entries.
    for entry in get_entries(scraping_url):
        entry_elem = ET.Element("entry")
        ET.SubElement(entry_elem, "title").text = entry["title"]
        ET.SubElement(entry_elem, "link", {"href": entry["url"]})
        ET.SubElement(entry_elem, "id").text = entry["id"]
        ET.SubElement(entry_elem, "updated").text = entry["date"]
        ET.SubElement(
            entry_elem, "summary", {"type": "html"}
        ).text = f'<a href="{entry["url"]}">Read the chapter on lightnoveltranslations.com</a>'

        feed.append(entry_elem)

    # Write XML document.
    ET.ElementTree(feed).write(feed_path, "utf-8", xml_declaration=True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate atom feed for lightnoveltranslations.com"
    )
    parser.add_argument("feed_path", help="where the feed should be written")
    return parser.parse_args()


scraping_url = "https://lightnovelstranslations.com/latest-updates/"
args = parse_args()

generate_feed(args.feed_path, scraping_url)
