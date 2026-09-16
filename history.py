import csv

from datetime import date
from pathlib import Path

# path to history database
path = Path('data') / "history.csv"

# fields i CSV history database
FIELDS = ['word', 'part_of_speech',
        'definition',
        'context',
        'date_searched',
        'bookmark',
        'id'
]

# max number of rows kept per (word, part_of_speech) combo
MAX_ENTRIES_PER_WORD = 3

def load_history() -> list:
    """
    Reads history.csv with csv.DictReader into a list of dicts;
    if the file doesn't exist, create it with the header row
    (id, word, part_of_speech, definition, date_searched, bookmark)
    and return an empty list
    """
    # if path exist, load in memory
    history = []
    if path.exists():
        with path.open(mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for entry in reader:
                history.append(entry)

    else:
        # create path
        with path.open(mode='w', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(FIELDS)

    return history

def _write_history(history: list) -> None:
    """
    internal helper, overwrites history.csv with the given
    rows using csv.DictWriter
    """
    with path.open(mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(history)

def save_search(word: str, part_of_speech: str, definition: str,
                 context: str | None = None) -> None:
    """
    Records a fresh search in the history.

    Matches existing rows by (word, part_of_speech), case-insensitive
    on word. If there are already MAX_ENTRIES_PER_WORD rows for that
    combo, the one with the oldest date_searched is evicted before the
    new row is added. context is stored for display only, it plays no
    part in matching.
    """
    history = load_history()

    # next id is one more than the highest id currently on file
    next_id = max((int(entry['id']) for entry in history), default=0) + 1

    # existing rows for the same (word, part_of_speech) combo
    matches = [
        entry for entry in history
        if entry['word'].lower() == word.lower()
        and entry['part_of_speech'] == part_of_speech
    ]

    if len(matches) >= MAX_ENTRIES_PER_WORD:
        oldest = min(matches, key=lambda entry: entry['date_searched'])
        history.remove(oldest)

    history.append({
        'word': word,
        'part_of_speech': part_of_speech,
        'definition': definition,
        'context': context or '',
        'date_searched': date.today().isoformat(),
        'bookmark': 'no',
        'id': str(next_id),
    })

    _write_history(history)

def touch_entry(entry_id: int) -> None:
    """
    Updates a row's date_searched to today, without calling the API or
    adding a new row. Used when the user picks a past entry from the
    history dropdown instead of running a fresh search.
    """
    history = load_history()

    for entry in history:
        if int(entry['id']) == int(entry_id):
            entry['date_searched'] = date.today().isoformat()
            break

    _write_history(history)

def delete_entry(entry_id: int) -> None:
    """
    Removes the row with the given id from the history.
    """
    history = load_history()
    history = [entry for entry in history if int(entry['id']) != int(entry_id)]
    _write_history(history)

def toggle_bookmark(entry_id: int) -> None:
    """
    Flips the bookmark field ('yes'/'no') of the row with the given id.
    """
    history = load_history()

    for entry in history:
        if int(entry['id']) == int(entry_id):
            entry['bookmark'] = 'no' if entry['bookmark'] == 'yes' else 'yes'
            break

    _write_history(history)

