# Local File Intelligence Agent

A local AI agent that answers natural-language questions about files on your
computer by calling real, read-only Python tools — not by guessing.

Everything runs on your own machine using [Ollama](https://ollama.com) and an
open-weight model (`qwen2.5-coder:7b`). No internet connection or cloud API
is required, so your file data never leaves your computer.

## What it does

- **Scan a folder** — list files, extensions, and sizes.
- **Find the largest files** in a folder.
- **Search files** by keyword in their names.
- **Suggest an organization plan** — groups files into categories
  (Documents, Images, Scripts, Shortcuts, Archives, Other) as a
  *suggestion only*. No files are ever moved, renamed, or deleted.

The AI model decides which tool to call based on your question, then a
Python function actually reads the filesystem and returns real data. The
model's final answer is based on that real data, not invented.

## Requirements

- Windows (tested), Python 3.14
- [Ollama](https://ollama.com) installed and running
- Model pulled locally:
  ```
  ollama pull qwen2.5-coder:7b
  ```
- Python package:
  ```
  pip install ollama
  ```

## How to run

1. Open a terminal in this project folder.
2. Run:
   ```
   python agent.py
   ```
3. Type a question, for example:
   ```
   Find the 5 largest files in C:\Users\<you>\Desktop
   Search for files with keyword python
   Suggest how to organize the files in C:\Users\<you>\Desktop
   ```
4. Type `exit` to quit.

## How it works

1. You type a question.
2. The question is sent to the local `qwen2.5-coder:7b` model via Ollama,
   along with a list of available tools (`scan_folder`,
   `find_largest_files`, `search_files`).
3. The model decides whether a tool is needed and, if so, which one.
4. The matching Python function runs against your real filesystem.
5. The tool's actual output is sent back to the model, which writes a
   final answer grounded in that data.

A small text-fallback parser is included because this model occasionally
writes a tool call as plain text instead of using the structured tool-call
format — the fallback detects and executes it either way, so tool calls work
reliably.

## Safety

- All tools are **read-only**. No file is ever moved, renamed, or deleted.
- The "organize" feature only ever produces a suggested plan as text.
- Tool-call loops are capped (max 5 per request) to avoid infinite loops.
- Errors (bad paths, permission issues, Ollama not running) are caught and
  reported clearly instead of crashing.

## Model and environment details

| Item | Value |
|---|---|
| Model | `qwen2.5-coder:7b` |
| Model size | ~4.7 GB |
| Model license | Open-weight (Qwen license, see Ollama model page) |
| Runtime | Ollama 0.40.11 |
| Quantization | Default Ollama quantization for this tag |
| Hardware used for testing | AMD Ryzen 7 8840HS, 24 GB RAM, Windows |
| External APIs | None — fully local |

## License

MIT License — see `LICENSE` file.

## Future work

- A confirmed, user-approved file-move/organize action (with a shown plan
  and explicit yes/no confirmation before any file is touched).
- Reading file contents for supported text file types, only when explicitly
  requested.
- A simple GUI instead of the terminal interface.
