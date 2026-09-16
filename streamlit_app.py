import streamlit as st

from api_call_lib import (
    build_prompt,
    make_request,
    parse_output,
    AnswerDeclinedError,
    UnexpectedAnswerError,
    OutputParsingError,
)
from history import delete_entry, load_history, save_search, toggle_bookmark, touch_entry

st.set_page_config(
    page_title="The Augmented Dictionary",
    page_icon="📖",
    layout="wide",
)

st.markdown(
    """
    <style>
    .title-band {
        background-color: #2e7d32;
        padding: 0.75rem 1rem;
        border-radius: 6px;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .title-band h1 {
        color: white;
        margin: 0;
        font-size: 1.6rem;
    }
    .st-key-left_panel {
        background-color: #2e557d;
        padding: 1rem;
        border-radius: 6px;
    }
    .st-key-left_panel h3,
    .st-key-left_panel p,
    .st-key-left_panel label {
        color: white;
    }
    .st-key-left_panel button,
    .st-key-left_panel button p {
        color: #1a1a1a !important;
    }
    .st-key-left_panel button {
        background-color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.5);
    }
    .st-key-left_panel button:hover {
        background-color: #f2f2f2;
        border-color: #ffffff;
    }
    </style>
    <div class="title-band">
        <h1>The Augmented Dictionary</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# Note: current_result no longer needs a matching "bookmarked" flag -
# see the bookmark section in the right column for why.
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "current_result_id" not in st.session_state:
    st.session_state.current_result_id = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None

left_col, right_col = st.columns([4, 5])

with left_col:
    with st.container(key="left_panel"):
        st.subheader("Search / History")

        with st.form("search_form"):
            word = st.text_input("Word", max_chars=30)
            context = st.text_input("Context (optional)", max_chars=200)
            submitted = st.form_submit_button("🔍 Search")

        if submitted:
            if not word.strip():
                st.session_state.error_message = "Enter a word to search."
            else:
                st.session_state.error_message = None
                prompt = build_prompt(word=word, context=context or None)
                try:
                    with st.spinner("Looking it up..."):
                        raw_message = make_request(prompt)
                        response = parse_output(raw_message)
                    new_id = save_search(
                        word=response["word"],
                        part_of_speech=response["part of speech"],
                        definition=response["definition"],
                        context=context or None,
                    )
                    st.session_state.current_result = response
                    st.session_state.current_result_id = new_id
                except (
                    AnswerDeclinedError,
                    UnexpectedAnswerError,
                    OutputParsingError,
                ) as e:
                    st.session_state.error_message = str(e)

        if st.session_state.error_message:
            st.error(st.session_state.error_message)

        st.divider()

        # --- history list, interactive ---
        # Loaded once per run - this is the single source of truth for
        # the whole page this run, including the bookmark section below
        # (which reuses this same list rather than caching its own
        # separate copy of any one row's bookmark status).
        history = load_history()
        if not history:
            st.caption("No history yet.")
        else:
            # date_searched now stores a full timestamp (down to the
            # second), not just a date, so it's unique enough on its own
            # - no need for the id tiebreaker this used before.
            history_sorted = sorted(
                history,
                key=lambda entry: entry["date_searched"],
                reverse=True,
            )
            for entry in history_sorted:
                context_text = entry["context"] or "no context"
                row_label_col, row_delete_col = st.columns([5, 1])

                with row_label_col:
                    clicked_restore = st.button(
                        f"{entry['word']} — {context_text}",
                        key=f"restore_{entry['id']}",
                        use_container_width=True,
                    )

                with row_delete_col:
                    clicked_delete = st.button(
                        "🗑️",
                        key=f"delete_{entry['id']}",
                    )

                if clicked_restore:
                    touch_entry(entry["id"])
                    st.session_state.current_result = {
                        "word": entry["word"],
                        "part of speech": entry["part_of_speech"],
                        "definition": entry["definition"],
                    }
                    st.session_state.current_result_id = entry["id"]
                    st.session_state.error_message = None
                    st.rerun()

                if clicked_delete:
                    delete_entry(entry["id"])
                    st.rerun()

with right_col:
    st.subheader("Result")
    result = st.session_state.current_result
    if result:
        title_col, bookmark_col = st.columns([4, 1])

        with title_col:
            st.markdown(f"### {result['word']} ({result['part of speech']})")

        with bookmark_col:
            current_id = st.session_state.current_result_id
            # Read the bookmark state straight from `history` (loaded
            # fresh at the top of this same run) instead of keeping a
            # second, hand-updated copy of it in session_state. history
            # is already the real, current contents of history.csv for
            # this run, so this can never drift out of sync with what's
            # actually saved - there's only one copy of the truth now,
            # not two that we were trying to keep matching by hand.
            is_bookmarked = False
            if current_id is not None:
                for entry in history:
                    if int(entry["id"]) == int(current_id):
                        is_bookmarked = entry["bookmark"] == "yes"
                        break

            label = "🔖 Bookmarked" if is_bookmarked else "🔖 Bookmark"
            if current_id is not None:
                if st.button(label, key="bookmark_toggle"):
                    toggle_bookmark(current_id)
                    st.rerun()

        st.write(result["definition"])
    else:
        st.caption("Search a word to see its definition here.")
