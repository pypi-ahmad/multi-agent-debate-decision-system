# Disclaimer

This software is provided under the [MIT License](LICENSE), **as is**, with no warranty of any kind.

## You run it. You own the data. You own the risk.

The Multi-Agent Debate Decision System is a **local** tool. You clone it, you install it, you start Streamlit, you bring **your** Ollama models or **your** API keys. The author does not process your data, host your debates, or store your documents.

**All data processed by the app is 100% your responsibility.** That includes:

- Decision questions, transcripts, huddle notes, and judge recommendations
- Uploaded PDFs, notes, source files, and zip archives
- Contents of `data/decisions.db` and `data/lancedb/`
- Anything a tool fetches (Wikipedia, DuckDuckGo Instant Answer) or a model returns
- Compliance with the terms of Ollama, OpenAI, Agnes AI, Google, or any other endpoint you configure

Do not feed the app secrets, personal data, or confidential files unless you accept that they may be sent to the providers you configured, written to local disk, or appear in markdown exports.

The app has **no authentication**. Anyone who can reach your Streamlit port can use that session. Do not expose port **8522** to the internet.

Outputs (including “confidence,” winners, and recommendations) are generated text. They are not legal, medical, financial, or professional advice. You decide what to do with them.

## Money

This project is free. **No financial help, donations, sponsorship, or paid support is needed or wanted.** Please do not send money.

## Community

Issues, pull requests, and honest bug reports are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SUPPORT.md](SUPPORT.md).
