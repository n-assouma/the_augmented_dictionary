# The Augmented Dictionary

A dictionary app powered by Claude (Anthropic's LLM). Instead of a fixed set of definitions, you look up a word or expression and can optionally give it context (a sentence, a domain, a source like a specific book) so the definition actually fits how the word is being used. This is especially useful for things a classic dictionary struggles with, like phrasal verbs, slang, or British English idioms.

Each search is saved to a local history, which you can browse, restore, bookmark, or delete, so repeat lookups don't need a new API call.

The app comes in two forms:
- A Streamlit web UI (`streamlit_app.py`), the main way to use it.
- A command line interface (`main.py`), useful for quick one-off lookups.

> **Note:** This project needs a Claude (Anthropic) API key to work. You can create one at [console.anthropic.com](https://console.anthropic.com). Using the API key may incur usage costs on your Anthropic account.

## Requirements

- Python 3.10 or later
- Git
- A Claude (Anthropic) API key

## Installation and setup

### 1. Clone the repository

```bash
git clone https://github.com/n-assouma/the_augmented_dictionary.git
cd the_augmented_dictionary
```

### 2. Create and activate a virtual environment

**macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt or PowerShell):**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install the dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your API key

Create a file named `.env` in the project's root folder and add your key to it:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 5. Run the app

To launch the Streamlit UI:

```bash
streamlit run streamlit_app.py
```

This opens the app in your browser. 

To use the CLI instead:

```bash
python main.py "word" -c "optional context sentence"
```

The CLI also lets you browse and restore past searches without making a new API call:

```bash
# Browse your search history
python main.py

# Restore a past search by its id (shown when browsing)
python main.py -r 3
```

## License

MIT
