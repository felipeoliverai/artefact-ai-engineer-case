"""Streamlit chat UI: `uv run streamlit run app.py`."""

import json

import streamlit as st

from emporio import clock
from emporio.agent import Agent

st.set_page_config(page_title="Empório da Música — Atendimento", page_icon="🎸")

EXAMPLES = [
    "Quais violões vocês têm até R$ 1000?",
    "Quanto custa o Takamine GD20?",
    "Qual o endereço da loja? Estão abertos agora?",
    "Me arrependi da compra, posso devolver meu pedido?",
]
GREETING = "Oi! Eu sou a Lia, assistente virtual da Empório da Música 🎶 Como posso ajudar?"


def new_session() -> None:
    st.session_state.agent = Agent()
    st.session_state.display = [{"role": "assistant", "content": GREETING, "tools": []}]


if "agent" not in st.session_state:
    new_session()
agent: Agent = st.session_state.agent

with st.sidebar:
    st.header("🎸 Empório da Música")
    st.caption("Protótipo de agente de atendimento")
    show_tools = st.toggle("Mostrar ferramentas consultadas", value=True)
    if st.button("Nova conversa", use_container_width=True):
        agent.reset()
        new_session()
        st.rerun()
    st.divider()
    st.caption(f"Modelo: `{agent.model}`")
    st.caption(f"Sessão: `{agent.session_id}`")
    st.caption(f"Data do agente: {clock.now():%d/%m/%Y %H:%M}")

st.title("Atendimento Empório da Música")


def render_tools(tools: list[dict]) -> None:
    if not (show_tools and tools):
        return
    with st.expander(f"🔧 {len(tools)} consulta(s) ao sistema"):
        for call in tools:
            st.markdown(f"**`{call['name']}`** `{json.dumps(call['arguments'], ensure_ascii=False)}`")
            st.json(call["result"], expanded=False)


for msg in st.session_state.display:
    with st.chat_message(msg["role"], avatar="🎸" if msg["role"] == "assistant" else None):
        render_tools(msg.get("tools", []))
        st.markdown(msg["content"])

prompt = st.chat_input("Digite sua mensagem...")
if len(st.session_state.display) == 1:
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLES):
        if cols[i % 2].button(example, use_container_width=True):
            prompt = example

if prompt:
    st.session_state.display.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🎸"):
        with st.spinner("Lia está digitando..."):
            reply = agent.chat(prompt)
        tools = [{"name": c.name, "arguments": c.arguments, "result": c.result} for c in reply.tool_calls]
        render_tools(tools)
        st.markdown(reply.text)
    st.session_state.display.append({"role": "assistant", "content": reply.text, "tools": tools})
    st.rerun()
