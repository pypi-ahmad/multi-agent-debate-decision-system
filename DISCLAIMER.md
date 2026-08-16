# Disclaimer

This software is provided under the [MIT License](LICENSE), **as is**, with no warranty of any kind.

## You run it. You own the risk.

The Multi-Agent Debate Decision System is a **local** tool. You clone it, you install it, you start Streamlit, you bring **your** Ollama models or **your** API keys. The author does not process your data, host your debates, or store your documents.

**Everything you type, upload, retrieve, or send to a model is 100% your responsibility.** That includes:

- Decision questions, transcripts, and judge recommendations
- Uploaded PDFs, notes, code, and zips
- Contents of `data/decisions.db` and `data/lancedb/`
- Anything a tool fetches (Wikipedia, DuckDuckGo) or a provider model returns
- Compliance with the terms of Ollama, OpenAI, Agnes AI, Google, or any other endpoint you point at

Do not feed the app secrets, personal data, or confidential files unless you accept that they may be sent to the providers you configured, written to local disk, or appear in exports.

The app has **no authentication**. Anyone who can reach your Streamlit port on your machine can use the session. Do not expose port **8522** to the internet.

Outputs (including “confidence,” winners, and recommendations) are generated text. They are not legal, medical, financial, or professional advice. You decide what to do with them.

## Money

This project is free. **No financial help, donations, sponsorship, or paid support is needed or wanted.** Please do not send money.

## Community

Issues, pull requests, and honest bug reports are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SUPPORT.md](SUPPORT.md).
