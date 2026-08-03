# Neohp: A simple Python style language that gets converted into PHP in real time.

Suitable for Web Design and light backend work by now. 

It aims to make it easier and faster to grab or manipulate data from backend with simple Python style commands, embedded right inside your html file. Inject any data to the html page, and the resulting php file is shown instantly on your server.

I have only implemented some functions that were useful on my day to day web development work and I wanted to simplify, by now.

Feel free to push more requests to the code with your custom functions to expand it, if you need it to have some function I didn't have time to implement!

If something is missing, you can combine this easy language syntax with any php code you want in the same .pyh file, as the interpreter will take php code as is, and it will be used on the output file.

Will give credit to contributors. 

Let's make something easier and funnier to use for our daily PHP development work!

Discord link | Contact Email | Donations | Documentation (just make it on markdown or txt format in another file, or html)


Usage:
1. Git clone repourl
2. python3 (projectname).py path-to-project - This will keep the interpreter running on the background and checking the .pyh files inside that project folder . Open another tab on the terminal or run it as a background command
3. Cd to your project folder
4. You can create a .pyh file, and when hitting save it will automatically generate a php file with the same name

For a seamless development environment, pass a 3rd parameter when calling projectname.py with the path to your test server, so it will automatically update the php file and you will see the changes on your server (3rd param is the output path for the generated php files)


Extra info:
- You can normally run functions with or without parentheses. For funcs with more than 2 params, it is recommended to use parentheses.