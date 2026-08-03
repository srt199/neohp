# Neohp

Neohp is a lightweight Python-style syntax layer that compiles into plain PHP.

It is designed for fast web prototyping: write short backend logic directly inside HTML pages, then it converts it into readable PHP files that can run on any standard hosting.

![Language](https://img.shields.io/badge/language-Python--style-blue)
![Output](https://img.shields.io/badge/output-PHP-777bb4)
![Status](https://img.shields.io/badge/status-early%20stage-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## Why Neohp

- Write less for common backend tasks.
- Keep template-like readability for designers.
- Reuse helper functions from one central helpers.php file.
- Keep generated output as normal PHP you can debug anywhere.

## How It Works

1. Write your page in a .pyh file.
2. Use #? and ?# to mark code blocks.
3. Run the interpreter.
4. Neohp generates a matching .php file.

HTML outside code blocks is preserved as-is.

## Project Structure

Expected base files:

- interpreter.py
- helpers.php
- config.pyh
- index.pyh
- lib/spaceFunctions.txt

Runtime output:

- Generated PHP files stay next to their .pyh source files.
- Shared runtime helpers are copied into target_dir/neohp/helpers.php.
- Generated files include that shared helper file using the correct relative path.

## Quick Start

Requirements:

- Python 3.9+
- PHP 8.0+

Install and compile:

	git clone https://github.com/srt199/neohp
	cd neohp
	python3 interpreter.py .

This command compiles every .pyh file under the target folder into a .php file with the same name.

Watch mode (auto-compile on save):

	python3 interpreter.py . --watch

Custom polling interval:

	python3 interpreter.py . --watch --interval 0.5

Help:

	python3 interpreter.py --help

Behavior:

- Watches the target directory recursively, including subdirectories.
- Detects changed or newly-created .pyh files.
- Generates the output .php file in the same directory as each .pyh source file.
- Copies the runtime helper file into target_dir/neohp/helpers.php.
- Makes each generated PHP file include that shared helper runtime path automatically.

## Minimal Example

Input file example.pyh:

	#?
	include config.pyh
	debug_on
	db = connectDb("dbName")
	users = dbQuery("SELECT * FROM users WHERE active = 1")
	?#

Generated example.php:

- Includes the shared runtime helper file from neohp/helpers.php automatically.
- Includes config.php (compiled from config.pyh).
- Executes standard PHP helper calls.

## Config Profiles (config.pyh)

Neohp supports profile-based DB config. The value passed to connectDb("profileId") maps to a profile set in config.pyh.

Example:

	#?
	setDbConfig("dbName", [driver->"mysql", host->"127.0.0.1", dbname->"neohp_app", username->"root", password->"", charset->"utf8mb4", default_table->"users"])
	setDefaultDb("dbName")
	setDefaultTable("users")
	setTelegramConfig("REPLACE_BOT_TOKEN", "REPLACE_CHAT_ID")
	?#

Then in any page:

	db = connectDb("dbName")

## Syntax Cheatsheet

Blocks:

- #? starts a PHP code block
- ?# ends a PHP code block

Common patterns:

- include config.pyh
- debug_on
- if condition:
- else statement
- try:
- except Exception as err:
- except:
- finally:
- foreach list as item:
- loopCsv "cities.csv" as city:

Shorthand examples:

- arrayPost = sanitize(getPost)
- url_slug = slugify getUrl
- product_name = slugToWord url_slug "fcaps"
- setSession "user_id" 5
- user_id = getSession "user_id"
- exit({"status": "success"})

## Built-in Helper Function Map

Neohp compiles shorthand to helper calls in helpers.php, including:

- sanitize
- connectDb
- select
- insert
- dbQuery
- postRequest
- httpRequest (via curl(...))
- pingTelegram
- slugify
- slugToWord
- parseValue (via parse(...))
- readCsv
- replaceInPageText
- setSession / getSession
- setLocalstorage / getLocalstorage
- redirect
- respondJson (via exit({...}))

## Notes for Contributors

- Keep generated PHP valid and readable.
- Prefer helper-based translations over inline complex PHP.
- Add new simple-call functions to lib/spaceFunctions.txt when needed.
- Keep examples realistic, with defined variables and valid params.

## Current Limitations

- I have only implemented some functions that were useful on my day to day web development work and I wanted to simplify, by now.
- Watch mode uses polling (mtime checks), not OS-level filesystem events.
- Some advanced nested shorthand patterns are still evolving.
- Multiline object literals in .pyh are limited; prefer single-line arrays for now.

## Roadmap Ideas

- Optional native filesystem events backend (faster than polling).
- Better multiline parsing for arrays and config blocks.
- Better diagnostics (line-level compile warnings).
- More helper presets for forms, auth, and CMS tasks.

## Contributing

Issues and pull requests are welcome.

If you propose a new syntax command, include:

1. Example .pyh input
2. Expected PHP output
3. Helper requirements (if any)

## License

MIT. See [LICENSE](LICENSE).