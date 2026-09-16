================================================================================
json2toon - Convert between JSON and TOON (Token-Optimized Object Notation)
================================================================================

Repository: https://github.com/bert2020-dev/json2toon/tree/main
License:    Apache License 2.0


--------------------------------------------------------------------------------
1. WHAT IT IS
--------------------------------------------------------------------------------

json2toon is a small, dependency-free command-line tool that converts data
between two text formats:

  * JSON  - JavaScript Object Notation, the ubiquitous data interchange format.
  * TOON  - Token-Optimized Object Notation, a compact, YAML-flavored,
            indentation-based format designed to use as few tokens (and as
            few characters) as possible while remaining human-readable.

The two directions are:

  JSON  ->  TOON      (compact the data, save tokens/bytes)
  TOON  ->  JSON      (expand back to a standard, machine-friendly format)

The direction is auto-detected from the input content, so you never have to
tell the tool which way you are going. A .json or .toon file extension, if
present, is used only as a hint (useful for producing clean error messages
on malformed input).


--------------------------------------------------------------------------------
2. WHAT IS TOON?
--------------------------------------------------------------------------------

TOON is a lightweight, indentation-based serialization format. It is similar
in spirit to YAML but is deliberately reduced to a minimal set of constructs
so that large, repetitive JSON payloads (arrays of records, for example) can
be encoded with dramatically fewer tokens.

Small example - a JSON object:

    {
      "user": {
        "id": 42,
        "name": "Alice",
        "tags": ["admin", "ops"]
      }
    }

...becomes this TOON:

    user:
      id: 42
      name: Alice
      tags[2]: admin,ops

And an array of uniform objects:

    {
      "users": [
        { "id": 1, "name": "Alice" },
        { "id": 2, "name": "Bob"   }
      ]
    }

...becomes this TOON:

    users[2]{id,name}:
      1,Alice
      2,Bob

The key TOON constructs supported by this tool are:

  * Scalars         key: value
  * Nested objects  key:  <newline>  <indented children>
  * Inline arrays   key[N]: v1,v2,v3
  * Tabular arrays key[N]{f1,f2,...}:   <-- uniform objects, one row per line
  * List items      - item           (for non-uniform arrays)
  * Comments        # ...            (lines starting with '#')
  * Quoting         "..." or '...'   (for strings with special characters)


--------------------------------------------------------------------------------
3. INSTALLATION
--------------------------------------------------------------------------------

json2toon is a single-file Python script. It has NO third-party dependencies.
All you need is Python 3.7 or newer (Python 3.8+ recommended).

3.1 Check your Python version
-----------------------------

    python3 --version

If you see something >= 3.7, you are good to go. If not, install Python 3
from your package manager or from https://www.python.org/downloads/.

3.2 Get the script
------------------

Option A - Clone the repository:

    git clone https://github.com/bert2020-dev/json2toon.git
    cd json2toon

Option B - Download just the file:

    curl -O https://raw.githubusercontent.com/bert2020-dev/json2toon/main/json2toon.py

3.3 Linux / macOS
-----------------

Make the script executable and put it on your PATH:

    chmod +x json2toon.py
    sudo mv json2toon.py /usr/local/bin/json2toon

Now you can invoke it directly:

    json2toon --help

If you prefer not to install it system-wide, just run it from wherever you
saved it:

    python3 ./json2toon.py --help

3.4 Windows
-----------

Option A - Run with the Python launcher (no install needed):

    py json2toon.py --help

Option B - Install as a command:

  1. Save json2toon.py somewhere permanent, e.g. C:\Tools\json2toon.py
  2. Add C:\Tools to your PATH:
       - Open "Edit the system environment variables"
       - Environment Variables -> User variables -> Path -> Edit -> New
       - Add C:\Tools
  3. Create a small wrapper C:\Tools\json2toon.cmd containing:

       @echo off
       py "%~dp0json2toon.py" %*

  4. Open a new terminal and run:

       json2toon --help

Option C - WSL / Git Bash:

  Follow the Linux instructions above inside WSL, Git Bash, or MSYS2.

3.5 Verify the installation
---------------------------

    json2toon --help

You should see the usage message. If you get "command not found", double
check that the directory containing the script is on your PATH.


--------------------------------------------------------------------------------
4. QUICK START
--------------------------------------------------------------------------------

4.1 Basic usage

    json2toon [input] [output] [-f|--force] [-h|--help]

  * input   - file to read, or "-" for stdin (default: stdin)
  * output  - file to write; "-" for stdout.
              Defaults to the input filename with the extension swapped,
              or stdout when reading from stdin.
  * -f, --force - overwrite the output file without prompting.
  * -h, --help  - show help and exit.

4.2 Examples

Convert a JSON file to TOON (creates data.toon next to data.json):

    json2toon data.json

Convert a TOON file back to JSON (creates data.json):

    json2toon data.toon

Write to an explicit output file:

    json2toon data.json out/data.toon

Write to stdout (useful for piping):

    json2toon data.json -

Read from stdin, write to stdout:

    cat data.json | json2toon -
    json2toon - < data.json

Overwrite an existing output file without being asked:

    json2toon data.json -f

Round-trip check (JSON -> TOON -> JSON should be equivalent):

    json2toon data.json data.toon
    json2toon data.toon -
    diff <(python3 -m json.tool data.json) <(json2toon data.toon -)

4.3 Example: shrinking a repetitive payload

Input (config.json):

    {
      "service": "api",
      "replicas": [
        { "id": 1, "region": "us-east-1", "healthy": true  },
        { "id": 2, "region": "us-west-2", "healthy": false },
        { "id": 3, "region": "eu-west-1", "healthy": true  }
      ]
    }

Command:

    json2toon config.json

Output (config.toon):

    service: api
    replicas[3]{id,region,healthy}:
      1,us-east-1,true
      2,us-west-2,false
      3,eu-west-1,true

Round-tripping this back to JSON with "json2toon config.toon -" produces the
original object.

4.4 Exit codes

    0   success
    1   I/O error (missing file, permission denied, user aborted overwrite)
    2   parse error (invalid JSON or invalid TOON)


--------------------------------------------------------------------------------
5. LIMITATIONS
--------------------------------------------------------------------------------

  * Scalars only inside tabular arrays.
    The key[N]{...} table form is only used when every element of the array
    is an object with the same keys and no nested objects or arrays as
    values. Otherwise json2toon falls back to a "- " list form.

  * No TOON specification versioning.
    TOON is not (yet) a formally standardized format. This tool implements
    the subset it emits, and tries to be lenient when reading. Files written
    by other TOON tools may not always parse.

  * Top-level scalars are allowed but unusual.
    A bare "42" or "hello" parses as a scalar, but most real usage is an
    object or an array at the top level.

  * Comments are dropped on round-trip.
    TOON input may contain '#' comment lines; they are ignored during
    parsing and are not preserved on output.

  * Key ordering is preserved, but JSON text formatting is not.
    Output JSON is always pretty-printed with 2-space indentation and
    UTF-8. Original whitespace or key order quirks in the source are not
    reproduced byte-for-byte.

  * No streaming / very large inputs.
    Files are read fully into memory. For inputs in the multi-gigabyte
    range, prefer a streaming tool such as jq.

  * Number fidelity.
    Integers and floats are handled via Python's native types. Extremely
    large integers are supported; JSON numbers with more precision than a
    Python float are subject to the usual float round-trip caveats.

  * No duplicate-key detection.
    Like most JSON parsers, the last duplicate key wins in a JSON object.

  * Line endings.
    Output uses '\n' on all platforms. Windows tools that require CRLF can
    convert the file afterward if needed.


--------------------------------------------------------------------------------
6. TROUBLESHOOTING
--------------------------------------------------------------------------------

Q: "json2toon: command not found" (Linux/macOS)
A: The script is not on your PATH. Either move it to /usr/local/bin, or
   invoke it as "python3 ./json2toon.py ...".

Q: "py: command not found" (Windows)
A: The Python launcher is not installed. Reinstall Python from python.org
   and make sure "Add Python to PATH" is checked, or use "python" instead
   of "py".

Q: "json2toon: error: <file>: invalid JSON: ..."
A: Your input file has a syntax error, and because its extension is .json
   (or its content looks like JSON), the tool tried to parse it as JSON.
   Fix the JSON, or rename the file so the extension does not claim JSON
   if the content is actually TOON.

Q: "json2toon: error: <file>: unexpected content at line N: ..."
A: Your TOON input has a line that could not be attached to any parent
   block. Usually this means the indentation is inconsistent. TOON uses
   spaces (not tabs) and requires child lines to be more indented than
   their parent.

Q: "json2toon: error: <file>: row has X cells, expected Y: ..."
A: A tabular array row has a different number of comma-separated values
   than the header declared. Check for stray commas, unquoted commas
   inside strings, or a mismatch between the {fields} list and the data.

Q: "json2toon: error: input is empty"
A: The file (or stdin) had no content. Nothing to convert.

Q: The output file already exists and I do not want the prompt.
A: Use -f / --force to overwrite without asking.

Q: Piping to a pager shows nothing.
A: Make sure you passed "-" as the output argument, e.g.
       json2toon data.json - | less

Q: Accented or non-ASCII characters look wrong.
A: All I/O is UTF-8. On Windows, run "chcp 65001" first if your console
   is not using UTF-8, or redirect to a file and open it in a UTF-8 editor.

Q: I want to see what version I am running.
A: There is no --version flag; the tool is a single script. Check the
   commit hash of your checkout, or the header comment of the file.

Q: Conversion is slow on a big file.
A: Parsing is pure Python. For very large inputs (hundreds of MB), consider
   jq for the JSON side and stream in chunks.


--------------------------------------------------------------------------------
7. CREDITS
--------------------------------------------------------------------------------

Author:   bert2020-dev
Homepage: https://github.com/bert2020-dev/json2toon

Thanks to the Python standard library, which is the only dependency.
Thanks to the wider TOON / token-efficient-serialization community for
inspiring the format's design goals.

If you find a bug or have a feature request, please open an issue at:
    https://github.com/bert2020-dev/json2toon/issues


--------------------------------------------------------------------------------
8. LICENSE
--------------------------------------------------------------------------------

Copyright (c) the json2toon contributors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

A copy of the full license text is included in the LICENSE file at the
root of the repository.

================================================================================
