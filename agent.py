import json
import re
from pathlib import Path
import ollama

MODEL = "qwen2.5-coder:7b"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "scan_folder",
            "description": (
                "Scan a user-selected folder and return its direct files, "
                "names, extensions, sizes, and summary. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path of the folder to scan."
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_largest_files",
            "description": (
                "Find the largest files in a user-selected folder using "
                "actual file sizes from the filesystem."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path of the folder."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of largest files to return."
                    }
                },
                "required": ["folder_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Search for filenames containing a keyword in a "
                "user-selected folder. Searches direct files only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_path": {
                        "type": "string",
                        "description": "Absolute path of the folder."
                    },
                    "keyword": {
                        "type": "string",
                        "description": "Text to search for in filenames."
                    }
                },
                "required": ["folder_path", "keyword"]
            }
        }
    }
]


def validate_folder(folder_path):
    folder = Path(folder_path).expanduser().resolve()

    if not folder.exists():
        return None, "Folder does not exist."

    if not folder.is_dir():
        return None, "The selected path is not a folder."

    return folder, None


def scan_folder(folder_path):
    folder, error = validate_folder(folder_path)
    if error:
        return {"error": error}

    files = []

    try:
        for item in folder.iterdir():
            if item.is_file():
                try:
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "extension": item.suffix.lower() or "no extension",
                        "size_bytes": stat.st_size
                    })
                except OSError:
                    continue
    except OSError as exc:
        return {"error": str(exc)}

    return {
        "folder": str(folder),
        "total_files": len(files),
        "total_size_bytes": sum(f["size_bytes"] for f in files),
        "files": files
    }


def find_largest_files(folder_path, limit=5):
    folder, error = validate_folder(folder_path)
    if error:
        return {"error": error}

    limit = max(1, min(int(limit), 20))
    results = []

    try:
        for item in folder.iterdir():
            if item.is_file():
                try:
                    results.append({
                        "name": item.name,
                        "size_bytes": item.stat().st_size
                    })
                except OSError:
                    continue
    except OSError as exc:
        return {"error": str(exc)}

    results.sort(key=lambda item: item["size_bytes"], reverse=True)

    return {
        "folder": str(folder),
        "largest_files": results[:limit]
    }


def search_files(folder_path, keyword):
    folder, error = validate_folder(folder_path)
    if error:
        return {"error": error}

    matches = []
    keyword = keyword.casefold()

    try:
        for item in folder.iterdir():
            if item.is_file() and keyword in item.name.casefold():
                matches.append({
                    "name": item.name,
                    "size_bytes": item.stat().st_size
                })
    except OSError as exc:
        return {"error": str(exc)}

    return {
        "folder": str(folder),
        "keyword": keyword,
        "matches": matches,
        "count": len(matches)
    }


def execute_tool(name, arguments):
    print(f"\n[TOOL CALL] {name}")
    print("[ARGUMENTS]", json.dumps(arguments, ensure_ascii=False))

    try:
        if name == "scan_folder":
            result = scan_folder(**arguments)
        elif name == "find_largest_files":
            result = find_largest_files(**arguments)
        elif name == "search_files":
            result = search_files(**arguments)
        else:
            result = {"error": "Unknown tool requested."}
    except (TypeError, ValueError, OSError) as exc:
        result = {"error": str(exc)}

    print("[TOOL RESULT]", json.dumps(result, ensure_ascii=False)[:1200])
    return result


TOOL_NAMES = {"scan_folder", "find_largest_files", "search_files"}


def try_extract_text_tool_call(content):
    """
    Some models occasionally print a tool call as plain JSON text instead of
    using the structured tool_calls field. This looks for a JSON object in
    the text that matches {"name": ..., "arguments": {...}} and returns it.
    Returns None if nothing matching is found.
    """
    if not content:
        return None

    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    name = data.get("name")
    arguments = data.get("arguments")

    if name in TOOL_NAMES and isinstance(arguments, dict):
        return name, arguments

    return None


def main():
    print("=" * 55)
    print("     LOCAL FILE INTELLIGENCE AGENT")
    print("     Powered by local Qwen AI + tool calling")
    print("=" * 55)
    print("Read-only: no files will be moved, changed, or deleted.")
    print("Example: Find the largest files on my Desktop.")
    print("Type exit to quit.\n")

    messages = [{
        "role": "system",
        "content": (
            "You are a careful local file intelligence agent. "
            "Use the available tools whenever the user asks about actual "
            "files, file sizes, folder contents, or filename searches. "
            "Never invent tool results. Base factual answers on tool output. "
            "If a folder path is not supplied, ask the user for it. "
            "Never claim to have modified files. Tools are read-only. "
            "Keep answers concise and explain what you actually checked. "
            "\n\n"
            "If the user asks you to organize, sort, or clean up a folder, "
            "first call scan_folder to see the real files. Then, based on "
            "file extensions and names, group them into clear categories "
            "(for example: Documents, Images, Scripts, Shortcuts, Archives, "
            "Other). Present this as a numbered plan showing which files "
            "would go into which category. Clearly state this is a "
            "SUGGESTION ONLY and that no files have been moved, since you "
            "have no tool to move files yet."
        )
    }]

    while True:
        user_input = input("You > ").strip()

        if user_input.lower() in {"exit", "quit"}:
            print("Agent stopped.")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            for _ in range(5):
                response = ollama.chat(
                    model=MODEL,
                    messages=messages,
                    tools=TOOLS
                )

                message = response["message"]
                messages.append(message)

                tool_calls = message.get("tool_calls")

                if not tool_calls:
                    extracted = try_extract_text_tool_call(message.get("content"))
                    if extracted:
                        name, arguments = extracted
                        result = execute_tool(name, arguments)
                        messages.append({
                            "role": "tool",
                            "name": name,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                        continue

                if not tool_calls:
                    print("\nAI >", message.get("content", "No response."))
                    break

                for tool_call in tool_calls:
                    name = tool_call["function"]["name"]
                    arguments = tool_call["function"]["arguments"]

                    result = execute_tool(name, arguments)

                    messages.append({
                        "role": "tool",
                        "name": name,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
            else:
                print("\nAgent stopped after reaching the tool-call limit.")

        except Exception as exc:
            print("\nCould not complete the request.")
            print("Check that Ollama is running and the model is available.")
            print("Details:", str(exc))
            messages = messages[:1]

        if len(messages) > 21:
            messages = [messages[0]] + messages[-20:]


if __name__ == "__main__":
    main()
