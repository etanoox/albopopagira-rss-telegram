import os
import json
import html
import feedparser
import requests
from pathlib import Path

FEED_URL = "https://feeds.feedburner.com/albopopagira"
STATE_FILE = Path("posted_items.json")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

MAX_ITEMS_PER_RUN = 15


def load_posted_items():
    if STATE_FILE.exists():
        try:
            return set(json.loads(STATE_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_posted_items(items):
    STATE_FILE.write_text(json.dumps(sorted(list(items)), indent=2))


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()


def build_message(entry):
    title = html.escape(entry.get("title", "Nuovo aggiornamento"))
    link = entry.get("link", "")

    published = entry.get("published", "")
    published_parsed = entry.get("published_parsed")

    if published_parsed:
        giorno = published_parsed.tm_mday
        mese = published_parsed.tm_mon
        anno = published_parsed.tm_year
        formatted_date = f"{giorno:02d}/{mese:02d}/{anno}"
    else:
        formatted_date = published

    message = f"""📌 <b>Nuovo aggiornamento dall'Albo Pretorio di Agira</b>

🗓 <b>Data pubblicazione:</b> {html.escape(formatted_date)}

<b>{title}</b>"""

    if link:
        message += f"\n\n🔗 <a href=\"{html.escape(link)}\">Leggi il documento</a>"

    message += "\n\n<i>Servizio informativo non ufficiale a cura di Albo Pop Agira.</i>"

    return message


def main():
    posted_items = load_posted_items()
    feed = feedparser.parse(FEED_URL)

    new_entries = []

    for entry in feed.entries:
        item_id = entry.get("id") or entry.get("guid") or entry.get("link")

        if not item_id:
            continue

        if item_id not in posted_items:
            new_entries.append((item_id, entry))

    # Pubblica dal più vecchio al più nuovo, così l’ordine nel canale è naturale
    new_entries = list(reversed(new_entries[:MAX_ITEMS_PER_RUN]))

    if not new_entries:
        print("Nessun nuovo elemento da pubblicare.")
        return

    for item_id, entry in new_entries:
        message = build_message(entry)
        send_telegram_message(message)
        posted_items.add(item_id)
        print(f"Pubblicato: {entry.get('title')}")

    save_posted_items(posted_items)


if __name__ == "__main__":
    main()
