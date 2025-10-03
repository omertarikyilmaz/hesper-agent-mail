# main.py
import os
import json
from typing import TypedDict, List
from datetime import timezone

from dotenv import load_dotenv
from imap_tools import MailBox, AND

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, START, END

# =========================
# Settings & Helpers
# =========================
load_dotenv()  # Read .env file

IMAP_HOST = os.getenv("IMAP_HOST")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
IMAP_FOLDER = "INBOX"

# Lightweight model with tool-calling support
CHAT_MODEL = "qwen2.5:3b"

# Ollama base: Get from env (e.g. OLLAMA_HOST="http://192.168.0.31:11434")
BASE_URL = os.getenv("OLLAMA_HOST")

def fmt_local(dt):
    """Safely convert and format to local timezone regardless of naive/aware."""
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone().strftime("%Y-%m-%d %H:%M")

# =========================
# State type
# =========================
class ChatState(TypedDict):
    messages: List[BaseMessage]

# =========================
# IMAP connection
# =========================
def connect():
    """Connect to IMAP server and enter INBOX; use with context manager to close when done."""
    mb = MailBox(IMAP_HOST)
    mb.login(IMAP_USER, IMAP_PASSWORD, initial_folder=IMAP_FOLDER)
    return mb

# =========================
# Tools
# =========================
@tool
def list_unread_emails() -> str:
    """Return JSON list of unread messages with uid, subject, date, sender."""
    print("List unread emails tool called.")

    with connect() as mb:
        unread = list(
            mb.fetch(
                criteria=AND(seen=False),
                headers_only=True,
                mark_seen=False,
            )
        )

    if not unread:
        return json.dumps([])

    data = [
        {
            "uid": mail.uid,  # usually int; goes to JSON without issues
            "date": fmt_local(mail.date),
            "subject": mail.subject,
            "sender": mail.from_,
        }
        for mail in unread
    ]
    return json.dumps(data)

@tool
def summarize_email(uid: str) -> str:
    """Summarize a single e-mail given its IMAP UID. Returns plain-text summary."""
    print("Summarize tool called.", uid)

    the_uid = str(uid).strip()
    with connect() as mb:
        mail = next(mb.fetch(AND(uid=the_uid), mark_seen=False), None)

    if not mail:
        return f"Could not summarize. UID not found: {uid}"

    body = mail.text if (mail.text and mail.text.strip()) else (mail.html or "")
    prompt = (
        "You are an assistant that summarizes emails clearly and concisely.\n"
        "Return a short summary.\n\n"
        f"Subject: {mail.subject}\n"
        f"Sender: {mail.from_}\n"
        f"Date: {fmt_local(mail.date)}\n\n"
        f"{body}"
    )
    return raw_llm.invoke(prompt).content

# =========================
# Models
# =========================
# Chat model that can call tools
llm = init_chat_model(
    CHAT_MODEL,
    model_provider="ollama",
    base_url=BASE_URL
).bind_tools([list_unread_emails, summarize_email])

# Raw model (doesn't call tools) - for email summarization
raw_llm = init_chat_model(
    CHAT_MODEL,
    model_provider="ollama",
    base_url=BASE_URL
)

# =========================
# Graph nodes
# =========================
def llm_node(state: ChatState) -> ChatState:
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

def router(state: ChatState) -> str:
    last = state["messages"][-1]
    # If AIMessage and has tool_calls, route to tools
    if isinstance(last, AIMessage):
        tc = getattr(last, "tool_calls", None)
        if tc:
            return "tools"
    return "end"

tool_node = ToolNode([list_unread_emails, summarize_email])

# =========================
# Graph construction
# =========================
builder = StateGraph(ChatState)
builder.add_node("llm", llm_node)
builder.add_node("tools", tool_node)

builder.add_edge(START, "llm")
builder.add_edge("tools", "llm")  # return to LLM after tool response
builder.add_conditional_edges("llm", router, {"tools": "tools", "end": END})

graph = builder.compile()

# =========================
# CLI loop
# =========================
if __name__ == "__main__":
    print("Using model:", CHAT_MODEL, "base_url:", BASE_URL)
    state: ChatState = {"messages": []}

    print('Type an instruction or "quit".\n')

    while True:
        user_message = input("> ")
        if user_message.lower() == "quit":
            break

        # Add as LangChain message object
        state["messages"].append(HumanMessage(content=user_message))

        # Run the graph
        state = graph.invoke(state)

        # Print the last response
        last = state["messages"][-1]
        print(last.content if isinstance(last, AIMessage) else str(last))
