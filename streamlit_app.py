"""
The Augmented Dictionary — Streamlit UI

Search bar on top, then two panels below: History / Bookmarked on the
left, the current entry on the right.

Run from this folder with: streamlit run streamlit_app.py
"""

import anthropic
import streamlit as st

from api_call_lib import (
    AnswerDeclinedError,
    OutputParsingError,
    UnexpectedAnswerError,
    build_prompt,
    make_request,
    parse_output,
)
from history import (
    delete_entry,
    load_history,
    save_search,
    toggle_bookmark,
    touch_entry,
)

WORD_MAX = 30
CONTEXT_MAX = 200
HISTORY_HEIGHT = 440

st.set_page_config(page_title="The Augmented Dictionary", page_icon="📖", layout="wide")

# ---------------------------------------------------------------- styling --
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800&family=Lora:ital,wght@0,400;0,500;0,600;1,400&display=swap');

    .stApp {
        background: #efe3c9;
    }

    h1, .headword { font-family: 'Playfair Display', Georgia, serif; }
    p, div, span, li, button { font-family: 'Lora', Georgia, serif; }

    .book-title {
        text-align: center;
        color: #2a2740;
        font-family: 'Playfair Display', Georgia, serif;
        font-weight: 800;
        margin-bottom: 1.6rem;
    }

    .st-key-left_panel, .st-key-right_panel {
        background: #fdfbf3;
        border: 1px solid #e4d6b8;
        border-radius: 20px;
        padding: 1.7rem 1.8rem;
        min-height: 420px;
        box-shadow: 0 10px 30px rgba(42, 39, 64, 0.05);
    }

    .headword {
        font-size: 2rem;
        font-weight: 800;
        color: #2a2740;
        margin-bottom: 0.1rem;
    }
    .pos-pill {
        display: inline-block;
        font-style: italic;
        letter-spacing: 0.02em;
        font-size: 0.82rem;
        color: #7a5a34;
        background: #f1e2c9;
        border-radius: 999px;
        padding: 0.25rem 0.8rem;
        margin: 0.4rem 0 0.9rem 0;
    }
    .definition {
        font-size: 1.05rem;
        line-height: 1.65;
        color: #3a3428;
    }
    .definition::first-letter {
        font-family: 'Playfair Display', Georgia, serif;
        font-size: 2.6rem;
        font-weight: 800;
        float: left;
        line-height: 0.8;
        margin: 0.02em 0.1em -0.1em 0;
        color: #b5502f;
    }
    .context-note {
        margin-top: 0.9rem;
        font-size: 0.85rem;
        font-style: italic;
        color: #8a7f68;
    }
    .empty-page {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 380px;
        color: #a89d84;
        text-align: center;
    }
    .empty-page .flourish { font-size: 2.4rem; margin-bottom: 0.6rem; }

    .history-row {
        border-bottom: 1px solid #eee2c8;
        padding: 0.5rem 0;
    }
    .history-word { font-weight: 700; color: #2a2740; }
    .history-meta { font-size: 0.78rem; font-style: italic; color: #8a7f68; }
    .history-context { font-size: 0.78rem; color: #8a7f68; margin-top: 0.15rem; }
    .history-time { font-size: 0.72rem; color: #a89d84; margin-top: 0.15rem; }
    .history-empty { color: #a89d84; font-style: italic; padding: 1rem 0; }

    div[data-testid="stForm"] {
        background: #fdfbf3;
        border: 1px solid #e4d6b8;
        border-radius: 20px;
        padding: 0.7rem 1.2rem;
        box-shadow: 0 10px 30px rgba(42, 39, 64, 0.06);
    }

    .stTabs [role="tab"] {
        font-weight: 600;
        color: #a89d84;
    }
    .stTabs [aria-selected="true"] {
        color: #2a2740 !important;
        border-bottom-color: #b5502f !important;
    }

    .st-key-left_panel button {
        border: 1px solid #e4d6b8 !important;
        border-radius: 8px !important;
        background: #fdfbf3 !important;
        color: #6b6152 !important;
    }

    .st-key-right_panel button[kind="primary"] {
        background: #b5502f !important;
        border-color: #b5502f !important;
        color: #fdfbf3 !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
    }
    .st-key-right_panel button[kind="secondary"] {
        background: #fdfbf3 !important;
        border: 1.5px solid #e4d6b8 !important;
        color: #2a2740 !important;
        border-radius: 999px !important;
        font-weight: 600 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------- session state --
if "result" not in st.session_state:
    st.session_state.result = None  # dict: word, pos, definition, id, context

# ------------------------------------------------------------------ header --
st.markdown('<h1 class="book-title">📖 The Augmented Dictionary</h1>', unsafe_allow_html=True)

# ------------------------------------------------------------- search bar --
with st.form(key="lookup_form", clear_on_submit=False):
    c_word, c_context, c_button = st.columns([2, 3, 1])
    with c_word:
        word_input = st.text_input(
            "Word", placeholder="a word or expression…", label_visibility="collapsed"
        )
    with c_context:
        context_input = st.text_input(
            "Context",
            placeholder="context (optional)",
            label_visibility="collapsed",
        )
    with c_button:
        submitted = st.form_submit_button("Look up ✒️", use_container_width=True)

if submitted:
    word = (word_input or "").strip()
    context = (context_input or "").strip() or None

    if not word:
        st.warning("Type a word or expression to look up.")
    elif len(word) > WORD_MAX:
        st.error(f"Keep the word/expression under {WORD_MAX} characters.")
    elif context and len(context) > CONTEXT_MAX:
        st.error(f"Keep the context under {CONTEXT_MAX} characters.")
    else:
        with st.spinner("Turning the pages…"):
            try:
                prompt = build_prompt(word=word, context=context)
                raw_message = make_request(prompt)
                response = parse_output(raw_message)
            except AnswerDeclinedError as e:
                st.error(str(e))
            except UnexpectedAnswerError as e:
                st.error(str(e))
            except OutputParsingError as e:
                st.error(str(e))
            except (anthropic.APIConnectionError, anthropic.APIStatusError) as e:
                st.error(f"Could not reach the dictionary service: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
            else:
                save_search(
                    word=response["word"],
                    part_of_speech=response["part of speech"],
                    definition=response["definition"],
                    context=context,
                )
                # save_search doesn't return the new id on this branch, so
                # recover it: the freshest row for this (word, pos) combo.
                fresh_history = load_history()
                matches = [
                    e for e in fresh_history
                    if e["word"].lower() == response["word"].lower()
                    and e["part_of_speech"] == response["part of speech"]
                ]
                entry_id = max((int(e["id"]) for e in matches), default=None)

                st.session_state.result = {
                    "word": response["word"],
                    "pos": response["part of speech"],
                    "definition": response["definition"],
                    "context": context,
                    "id": entry_id,
                }
                st.rerun()

# ------------------------------------------------------------ the two panels --
left_page, right_page = st.columns(2)

with left_page:
    with st.container(key="left_panel"):
        tab_history, tab_bookmarked = st.tabs(["History", "Bookmarked"])

        history = load_history()
        history_sorted = sorted(
            history, key=lambda e: (e["date_searched"], int(e["id"])), reverse=True
        )

        def render_rows(rows, scope):
            if not rows:
                st.markdown(
                    '<p class="history-empty">Nothing here yet.</p>', unsafe_allow_html=True
                )
                return
            for entry in rows:
                row_cols = st.columns([5, 1, 1])
                with row_cols[0]:
                    context_html = (
                        f'<div class="history-context">in: {entry["context"]}</div>'
                        if entry["context"] else ""
                    )
                    st.markdown(
                        f'<div class="history-row">'
                        f'<span class="history-word">{entry["word"]}</span> '
                        f'<span class="history-meta">({entry["part_of_speech"]})'
                        f'{" · ★" if entry["bookmark"] == "yes" else ""}</span>'
                        f"{context_html}"
                        f'<div class="history-time">{entry["date_searched"]}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with row_cols[1]:
                    if st.button("↺", key=f"restore_{scope}_{entry['id']}", help="Restore"):
                        touch_entry(entry["id"])
                        st.session_state.result = {
                            "word": entry["word"],
                            "pos": entry["part_of_speech"],
                            "definition": entry["definition"],
                            "context": entry["context"] or None,
                            "id": int(entry["id"]),
                        }
                        st.rerun()
                with row_cols[2]:
                    if st.button("🗑", key=f"delete_{scope}_{entry['id']}", help="Delete"):
                        delete_entry(entry["id"])
                        if (
                            st.session_state.result
                            and st.session_state.result.get("id") == int(entry["id"])
                        ):
                            st.session_state.result = None
                        st.rerun()

        with tab_history:
            with st.container(height=HISTORY_HEIGHT):
                render_rows(history_sorted, scope="history")
        with tab_bookmarked:
            with st.container(height=HISTORY_HEIGHT):
                render_rows(
                    [e for e in history_sorted if e["bookmark"] == "yes"],
                    scope="bookmarked",
                )

with right_page:
    with st.container(key="right_panel"):
        result = st.session_state.result

        if not result:
            st.markdown(
                '<div class="empty-page"><div class="flourish">❦</div>'
                "<div>Look up a word above to open its entry.</div></div>",
                unsafe_allow_html=True,
            )
        else:
            title_col, bookmark_col = st.columns([5, 2])
            with title_col:
                st.markdown(
                    f'<div class="headword">{result["word"]}</div>'
                    f'<div class="pos-pill">{result["pos"]}</div>',
                    unsafe_allow_html=True,
                )
            with bookmark_col:
                is_bookmarked = False
                if result.get("id") is not None:
                    current = next(
                        (e for e in load_history() if int(e["id"]) == result["id"]), None
                    )
                    is_bookmarked = bool(current and current["bookmark"] == "yes")

                label = "★ Bookmarked" if is_bookmarked else "☆ Bookmark"
                if st.button(
                    label,
                    key="bookmark_toggle",
                    type="primary" if is_bookmarked else "secondary",
                    disabled=result.get("id") is None,
                ):
                    toggle_bookmark(result["id"])
                    st.rerun()

            st.markdown(
                f'<div class="definition">{result["definition"]}</div>',
                unsafe_allow_html=True,
            )
            if result.get("context"):
                st.markdown(
                    f'<div class="context-note">as used in: “{result["context"]}”</div>',
                    unsafe_allow_html=True,
                )
