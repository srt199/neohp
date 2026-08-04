# Neohp - Python-style language converter to PHP

It allows to use Python-like easy code inside website files, with no compilation times or frameworks: Write short backend logic directly inside HTML pages, then it converts automatically into PHP files that can be uploaded and run on any standard hosting.

![Language](https://img.shields.io/badge/language-Python--style-blue)
![Output](https://img.shields.io/badge/output-PHP-777bb4)
![Status](https://img.shields.io/badge/status-early%20stage-orange)
![License](https://img.shields.io/badge/license-MIT-green)

## Why Neohp

- Easier, faster syntax for common PHP functions.
- Python style code you can embed inside your HTML + JS files to handle data. No compile times like frameworks.
- Generates normal PHP files you can deploy anywhere.
- The aim is to **replace clunky, slow frameworks and go back to basics**. Files that contain all HTML, JS, CSS and Backend code that are run by any server and shown immediately in any browser. All of PHP's advantages, deployment speed and compatibility, but with Python's more modern syntax.
- Current version aimed for web design and light backend tasks (You can also use any PHP code you want next to the python-style code, when you need more functions still not implemented)

## How It Works

1. Run the interpreter.
2. Write your pages in .pyh files.
3. Use #? and ?# to mark code blocks.
4. Neohp generates matching .php files instantly.

HTML outside code blocks is preserved as-is.

## Project Structure

Expected base files:

- interpreter.py
- helpers.php
- config.pyh
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

example.pyh:
```python
	#?
	include config.pyh
	debug_on

    arrayPost = sanitize(getPost)
	db = connectDb("dbName")
    dbData = select(db, "active = 1")

    foreach dbData as row:
        if row.email == "john@gmail.com" :
            email = "Email found"
            break

    if arrayPost.customer == "on":
        isSale = TRUE
    else isSale = FALSE

    #More example funcs

    insert(db, tableName, name -> "james")
    array1 = [name->"john", email->"john@gmail.com"]
    insert(db, tableName, array1)

    loopCsv "cities.csv" as city:
        cityPreview = city
        break
    ?#
    <!-- End tags and back to html -->
    <div> <p> #? print cityPreview ?# </p> </div>
    <!-- MORE HTML CODE ... -->
    #?
    pingTelegram("", "This is your message") 

    postRequest(url, [name->"john", email->"john@gmail.com"], headers)

    ?#
    <!-- ANY HTML, PHP, JS CODE IN ANY PLACE WORKS. JUST CLOSE NEOHP TAGS  -->
    <span> Hello #? print name ?# </span>

    #?
    redirect "https://weblabs.es"

    setSession "user_id" 5
    user_id = getSession "user_id"
    setLocalstorage "email" "john@gmail.com"
    email1 = getLocalstorage "email"

    users = dbQuery("SELECT * FROM users WHERE active = 1") #run any query

    response = curl(url, "post", headers, arrayData)
    response_ok = response.ok
    response_status = response.status
    api_payload = response.body

    exit({"status": "success", "http_status": response_status, "ok": response_ok, "api": api_payload}) #exits and returns json headers
    ?#
```

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

- Feel free to add support for any missing functions that you need
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