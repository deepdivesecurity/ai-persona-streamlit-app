import datetime
import os
from openai import OpenAI
import streamlit as st
from htbuilder.units import rem
from htbuilder import div, styles
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)

import me

from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Configuration
load_dotenv()
MODEL = os.getenv("MODEL")
MODEL_BASE_URL = os.getenv("MODEL_URL")

SUGGESTIONS = {
    ":blue[:material/local_library:] How many years of experience do you have in cybersecurity?": (
        "How many years of experience do you have in cybersecurity?"
    ),
    ":green[:material/database:] What certifications do you hold?": (
        "What certifications do you hold?"
    ),
    ":orange[:material/multiline_chart:] Tell me about your experience with DevSecOps": (
        "Tell me about your experience with DevSecOps"
    ),
    ":violet[:material/apparel:] How would your colleagues describe you?": (
        "How would your colleagues describe you?"
    ),
    ":red[:material/deployed_code:] Where can I find out more about you?": (
        "Where can I find out more about you?"
    ),
}

# Set page title and icon
st.set_page_config(page_title="Page Title Placeholder", page_icon="")
    
# def get_secret(secret_id: str, project_id: str = None) -> str:
#     """
#     Fetches a secret from Google Secret Manager

#     Args:
#         secret_id: Name of the secret in Secret Manager.
#         project_id: GCP project ID.

#     Returns:
#         Secret value as a string.
#     """
#     project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
#     if not project_id:
#         raise ValueError("Project ID not provided and GOOGLE_CLOUD_PROJECT not set")

#     client = secretmanager.SecretManagerServiceClient()
#     name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
#     response = client.access_secret_version(request={"name": name})
#     return response.payload.data.decode("UTF-8")

ai_api_key = os.getenv("AI_API_KEY")

# -----------------------------------------------------------------------------
# Dialogs
@st.dialog("Legal disclaimer")
def show_disclaimer_dialog():
    st.caption("""
            This website may use cookies. Some cookies are essential for the website to function.
            By continuing to use this site, you consent to the use of cookies.
        """)

# -----------------------------------------------------------------------------
# Retry logic for API calls
@retry(
    stop=stop_after_attempt(5),
    wait=wait_random_exponential(min=1, max=10),
    reraise=True
)
def fetch_chat_response(messages):
    """
    Sends a chat request to the LLM API with retry on failures
    """
    stream = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        stream=True,
    )
    return stream

# -----------------------------------------------------------------------------
# Clients / Instances

def get_openai_client():
    return OpenAI(
        base_url=MODEL_BASE_URL,
        api_key=ai_api_key,
    )

if "openai_client" not in st.session_state:
    st.session_state.openai_client = get_openai_client()

openai = st.session_state.openai_client

@st.cache_resource
def load_me():
    return me.Me()

me_instance = load_me()

# -----------------------------------------------------------------------------
# UI
st.html(div(style=styles(font_size=rem(5), line_height=1)))

title_row = st.container(
    horizontal=True,
    vertical_alignment="bottom",
)

with title_row:
    st.title(
        "Resume's are boring... ask me a question!",
        anchor=False,
        width="stretch",
    )

# -----------------------------------------------------------------------------
# Session-state helpers
user_just_asked_initial_question = (
    "initial_question" in st.session_state and st.session_state.initial_question
)

user_just_clicked_suggestion = (
    "selected_suggestion" in st.session_state and st.session_state.selected_suggestion
)

user_first_interaction = (
    user_just_asked_initial_question or user_just_clicked_suggestion
)

has_message_history = (
    "messages" in st.session_state and len(st.session_state.messages) > 0
)

# -----------------------------------------------------------------------------
# Initial landing UI
if not user_first_interaction and not has_message_history:
    with st.container():
        st.chat_input("Ask a question...", key="initial_question")

        st.pills(
            label="Examples",
            label_visibility="collapsed",
            options=SUGGESTIONS.keys(),
            key="selected_suggestion",
            # disabled=chat_disabled,
        )

    st.button(
        "&nbsp;:small[:gray[:material/balance: Legal disclaimer]]",
        type="tertiary",
        on_click=show_disclaimer_dialog,
    )

    st.stop()

# -----------------------------------------------------------------------------
# Normal chat mode
user_message = st.chat_input("Ask a follow-up question...")

if not user_message:
    if user_just_asked_initial_question:
        user_message = st.session_state.initial_question
    elif user_just_clicked_suggestion:
        user_message = SUGGESTIONS[st.session_state.selected_suggestion]

# Restart button
with title_row:

    def clear_conversation():
        st.session_state.messages = []
        st.session_state.initial_question = None
        st.session_state.selected_suggestion = None

    st.button(
        "Restart",
        icon=":material/refresh:",
        on_click=clear_conversation,
    )

# -----------------------------------------------------------------------------
# Initialize message history

if "messages" not in st.session_state or len(st.session_state.messages) == 0:
    st.session_state.messages = [
        {"role": "system", "content": me_instance.system_prompt()}
    ]

if "prev_question_timestamp" not in st.session_state:
    st.session_state.prev_question_timestamp = datetime.datetime.fromtimestamp(0)

# -----------------------------------------------------------------------------
# Display chat history
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.container()
        st.markdown(message["content"], unsafe_allow_html=False)

# -----------------------------------------------------------------------------
# Handle new message
if user_message:
    user_message = user_message.replace("$", r"\$")

    with st.chat_message("user"):
        st.text(user_message)

    st.session_state.messages.append(
        {"role": "user", "content": user_message}
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            messages_payload = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            response = None

            try:
                stream = fetch_chat_response(messages_payload)
                response = st.write_stream(stream)
            except Exception as e:
                st.error("""
                         Failed to get a response after multiple attempts.
                         This could mean that the API is temporarily unavailable or the daily limit has been reached.
                         Please try again later.""")
                response = "Sorry, something went wrong. Please try again."

    st.session_state.messages.append(
        {"role": "assistant", "content": response}
    )