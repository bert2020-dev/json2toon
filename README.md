# json2toon

**Convert between JSON and TOON (Token-Optimized Object Notation)**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/Dependencies-None-brightgreen.svg)](#installation)

A small, dependency-free command-line tool that converts data between **JSON** and **TOON** — a compact, YAML-flavored, indentation-based format designed to use as few tokens (and as few characters) as possible while remaining human-readable.

| Direction | Purpose |
|-----------|---------|
| **JSON → TOON** | Compact the data, save tokens & bytes |
| **TOON → JSON** | Expand back to a standard, machine-friendly format |

The direction is **auto-detected** from the input content — you never have to tell the tool which way you are going.

---

## What is TOON?

TOON is a lightweight, indentation-based serialization format. It is similar in spirit to YAML but deliberately reduced to a minimal set of constructs so that large, repetitive JSON payloads (arrays of records, for example) can be encoded with dramatically fewer tokens.

### Quick examples

**JSON object:**

```json
{
  "user": {
    "id": 42,
    "name": "Alice",
    "tags": ["admin", "ops"]
  }
}
```

**becomes this TOON:**

```toon
user:
  id: 42
  name: Alice
  tags[2]: admin,ops
```

**Array of uniform objects:**

```json
{
  "users": [
    { "id": 1, "name": "Alice" },
    { "id": 2, "name": "Bob" }
  ]
}
```

**becomes this TOON:**

```toon
users[2]{id,name}:
  1,Alice
  2,Bob
```

### Supported TOON constructs

| Construct | Syntax | Description |
|-----------|--------|-------------|
| Scalars | `key: value` | Simple key-value pairs |
| Nested objects | `key:` + indented children | Hierarchical structure |
| Inline arrays | `key[N]: v1,v2,v3` | Compact lists |
| Tabular arrays | `key[N]{f1,f2,...}:` | Uniform objects, one row per line |
| List items | `- item` | Non-uniform arrays |
| Comments | `# ...` | Lines starting with `#` |
| Quoting | `"..."` or `'...'` | Strings with special characters |

---

## Installation

`json2toon` is a **single-file Python script** with **no third-party dependencies**. All you need is **Python 3.7+** (3.8+ recommended).

### 1. Check your Python version

```bash
python3 --version
```

### 2. Get the script

**Option A — Clone the repository:**

```bash
git clone https://github.com/bert2020-dev/json2toon.git
cd json2toon
```

**Option B — Download just the file:**

```bash
curl -O https://raw.githubusercontent.com/bert2020-dev/json2toon/main/json2toon.py
```

### 3. Linux / macOS

Make the script executable and put it on your `PATH`:

```bash
chmod +x json2toon.py
sudo mv json2toon.py /usr/local/bin/json2toon
```

Then simply run:

```bash
json2toon --help
```

Or run it directly without installing:

```bash
python3 ./json2toon.py --help
```

### 4. Windows

**Option A — Run with the Python launcher (no install needed):**

```bash
py json2toon.py --help
```

**Option B — Install as a command:**

1. Save `json2toon.py` somewhere permanent, e.g. `C:\Tools\json2toon.py`
2. Add `C:\Tools` to your `PATH`
3. Create a wrapper `C:\Tools\json2toon.cmd`:

   ```bat
   @echo off
   py "%~dp0json2toon.py" %*
   ```

4. Open a new terminal and run:

   ```bash
   json2toon --help
   ```

**Option C — WSL / Git Bash:** Follow the Linux instructions inside WSL, Git Bash, or MSYS2.

### 5. Verify the installation

```bash
json2toon --help
```

You should see the usage message. If you get “command not found”, double-check that the directory containing the script is on your `PATH`.

---

## Quick Start

### Basic usage

```bash
json2toon [input] [output] [-f|--force] [-h|--help]
```

| Argument | Description |
|----------|-------------|
| `input` | File to read, or `-` for stdin (default: stdin) |
| `output` | File to write; `-` for stdout. Defaults to the input filename with the extension swapped, or stdout when reading from stdin |
| `-f`, `--force` | Overwrite the output file without prompting |
| `-h`, `--help` | Show help and exit |

### Examples

```bash
# Convert JSON → TOON (creates data.toon next to data.json)
json2toon data.json

# Convert TOON → JSON (creates data.json)
json2toon data.toon

# Write to an explicit output file
json2toon data.json out/data.toon

# Write to stdout (useful for piping)
json2toon data.json -

# Read from stdin, write to stdout
cat data.json | json2toon -
json2toon - < data.json

# Overwrite an existing output file without being asked
json2toon data.json -f
```

**Round-trip check** (JSON → TOON → JSON should be equivalent):

```bash
json2toon data.json data.toon
json2toon data.toon -
diff <(python3 -m json.tool data.json) <(json2toon data.toon -)
```

### Example: shrinking a repetitive payload

**Input (`config.json`):**

```json
{
  "service": "api",
  "replicas": [
    { "id": 1, "region": "us-east-1", "healthy": true  },
    { "id": 2, "region": "us-west-2", "healthy": false },
    { "id": 3, "region": "eu-west-1", "healthy": true  }
  ]
}
```

**Command:**

```bash
json2toon config.json
```

**Output (`config.toon`):**

```toon
service: api
replicas[3]{id,region,healthy}:
  1,us-east-1,true
  2,us-west-2,false
  3,eu-west-1,true
```

Round-tripping this back to JSON with `json2toon config.toon -` produces the original object.

### Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | I/O error (missing file, permission denied, user aborted overwrite) |
| `2` | Parse error (invalid JSON or invalid TOON) |

---

## Limitations

- **Scalars only inside tabular arrays** — The `key[N]{...}` table form is only used when every element of the array is an object with the same keys and no nested objects or arrays as values. Otherwise the tool falls back to a `- ` list form.
- **No TOON specification versioning** — TOON is not (yet) a formally standardized format. This tool implements the subset it emits and tries to be lenient when reading. Files written by other TOON tools may not always parse.
- **Top-level scalars are allowed but unusual** — A bare `42` or `hello` parses as a scalar, but most real usage is an object or an array at the top level.
- **Comments are dropped on round-trip** — TOON input may contain `#` comment lines; they are ignored during parsing and are not preserved on output.
- **Key ordering is preserved, but JSON text formatting is not** — Output JSON is always pretty-printed with 2-space indentation and UTF-8.
- **No streaming / very large inputs** — Files are read fully into memory. For multi-gigabyte inputs, prefer a streaming tool such as `jq`.
- **Number fidelity** — Integers and floats are handled via Python’s native types. Extremely large integers are supported; JSON numbers with more precision than a Python float are subject to the usual float round-trip caveats.
- **No duplicate-key detection** — Like most JSON parsers, the last duplicate key wins in a JSON object.
- **Line endings** — Output uses `\n` on all platforms. Windows tools that require CRLF can convert the file afterward if needed.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `json2toon: command not found` (Linux/macOS) | The script is not on your `PATH`. Move it to `/usr/local/bin` or invoke it as `python3 ./json2toon.py ...`. |
| `py: command not found` (Windows) | The Python launcher is not installed. Reinstall Python from [python.org](https://www.python.org) and make sure “Add Python to PATH” is checked, or use `python` instead of `py`. |
| `invalid JSON: ...` | Your input file has a syntax error. Fix the JSON, or rename the file so the extension does not claim JSON if the content is actually TOON. |
| `unexpected content at line N: ...` | Indentation is inconsistent. TOON uses spaces (not tabs) and requires child lines to be more indented than their parent. |
| `row has X cells, expected Y: ...` | A tabular array row has a different number of comma-separated values than the header declared. Check for stray commas or a mismatch between the `{fields}` list and the data. |
| `input is empty` | The file (or stdin) had no content. |
| Output file already exists and I don’t want the prompt | Use `-f` / `--force` to overwrite without asking. |
| Piping to a pager shows nothing | Pass `-` as the output argument: `json2toon data.json - \| less` |
| Accented or non-ASCII characters look wrong | All I/O is UTF-8. On Windows, run `chcp 65001` first if your console is not using UTF-8, or redirect to a file and open it in a UTF-8 editor. |
| Conversion is slow on a big file | Parsing is pure Python. For very large inputs (hundreds of MB), consider `jq` for the JSON side and stream in chunks. |

> There is no `--version` flag. Check the commit hash of your checkout or the header comment of the file.

---

## Credits

**Author:** [bert2020-dev](https://github.com/bert2020-dev)  
**Homepage:** [https://github.com/bert2020-dev/json2toon](https://github.com/bert2020-dev/json2toon)

Thanks to the Python standard library, which is the only dependency.  
Thanks to the wider TOON / token-efficient-serialization community for inspiring the format’s design goals.

Found a bug or have a feature request? Please open an issue at:  
[https://github.com/bert2020-dev/json2toon/issues](https://github.com/bert2020-dev/json2toon/issues)

---

## License

Copyright (c) the json2toon contributors.

Licensed under the **Apache License, Version 2.0**.

You may obtain a copy of the License at:  
[http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

A copy of the full license text is included in the `LICENSE` file at the root of the repository.
