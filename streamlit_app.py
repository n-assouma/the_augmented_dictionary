import streamlit as st

from api_call_lib import (
    build_prompt,
    make_request,
    parse_output,
    AnswerDeclinedError,
    UnexpectedAnswerError,
    OutputParsingError,
)

# Phase 2: real search + result display. History still not wired in
# (that's phase 3) - a fresh search is not saved to history.csv yet.

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
    </style>
    <div class="title-band">
        <h1>The Augmented Dictionary</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- session state -----------------------------------------------------
# Streamlit reruns this entire script top to bottom on every interaction
# (typing, clicking a button, etc). A plain Python variable would reset
# every time that happens, so anything that needs to survive from one
# rerun to the next - like "what result is currently on screen" - has to
# live in st.session_state instead, which Streamlit keeps around for the
# whole browser session. We only set the defaults the first time the
# script runs; on every later rerun this block does nothing, so the
# stored value is left untouched.
if "current_result" not in st.session_state:
    st.session_state.current_result = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None

left_col, right_col = st.columns([4, 5])

with left_col:
    with st.container(key="left_panel"):
        st.subheader("Search / History")

        # st.form batches the widgets inside it: typing in the boxes does
        # NOT rerun the script on every keystroke (unlike a bare
        # st.text_input placed directly on the page). The script only
        # reacts once, when the submit button is pressed, and word/
        # context/submitted below are that submission's values.
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
                    st.session_state.current_result = response
                except (
                    AnswerDeclinedError,
                    UnexpectedAnswerError,
                    OutputParsingError,
                ) as e:
                    st.session_state.error_message = str(e)

        if st.session_state.error_message:
            st.error(st.session_state.error_message)

        st.caption("History list will go here in phase 3.")

with right_col:
    st.subheader("Result")
    result = st.session_state.current_result
    if result:
        st.markdown(f"### {result['word']} ({result['part of speech']})")
        st.write(result["definition"])
    else:
        st.caption("Search a word to see its definition here.")