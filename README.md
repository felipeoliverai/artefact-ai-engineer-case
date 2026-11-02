# Empório da Música — Customer Service Agent

Prototype of a text-based customer-service agent for **Empório da Música**, a (fictional) musical
instrument store in Campo Grande/MS. Built for the Artefact AI Engineer technical case.

> Work in progress — full setup instructions, design decisions and limitations will be documented here.

## Stack (planned)

- **Python 3.11+**, managed with [uv](https://docs.astral.sh/uv/)
- **Ollama** (local LLM, no paid provider) with native tool calling
- **Streamlit** chat UI + a CLI for debugging
- Typed tools over a cleaned pandas data layer; store policies split by section
