# CTF-OvO-Manager
The CTF OvO Manager is an application helping with effective task distribution during team CTFs along with your team members

**PLEASE, read the following "Reflection" section before looking to my code!**

![CTF OvO Manager logo](Logo.png)

# Reflection
## Archiving reason
I am archiving this repository because the code in it is old, is not being supported for a long time and its author (me) feels **CRINGED/ASHAMED** about it. Things I find the worst parts of this code are:
### Tests
When writing this I had almost no idea about how unit tests must be created, so the way of testing in this project is extremely ugly. Sorry about that. In fact, you would better not go to the tests directory at all.
### Working with MySQL
I am not 100% sure, but I think, this was my first experience with MySQL. I have worked with SQLite before, but not long enough to learn how to design good SQL databases. But in fact, excluding creation of a new database for each game, I don't find my tables definitions very bad (even though I am not using some features MySQL provides for me which would come in handy in some cases). What I find a more important shit is how I work with my databases from my Python code. Lots of code duplication and multiple loads of database connections, creations of dangling cursors and so on makes me very sad :(

Btw, I think an ORM would be extremely handy for this project, but at the moment of writing it, I didn't even know what an ORM is...
### Other crap
There also are many places where I make some small (or not) mistakes or do something very questionable (for example, combining `os.path` and `Pathlib`.....) or the creepy way of how I parse command-line arguments (I did know about the `argparse` library, but didn't use it in purpose, which I am not going to explain here, because I am too lazy)
## Not deleting reason
On the other hand, I am not deleting this repository completely. That's because working on the project was a great experience for me, in those times. Despite I don't like the code now, I have rather cool memories of how I was developing this. If I am not mistaken, this was the first time when I was using Python docstrings! Isn't it great? I was thinking about documenting all this a lot. I have written lots of documentation before even starting to code! Designing the project's architecture, thinking about what end users are going to need and so on - this all was very cool. I remember exactly this part of developing CTF OvO Manager with the most warmth
## What should YOU do with this stuff?
It depends on what is your goal. I see three possible reasons for you to be here, choose the most appropriate section:
### You want to get to know me and my code
Hey, great! This highly likely means you are in the wrong place, but I am not sure, which is a good one... So, if you have read all the above, you can try to read the code, **BUT KEEP IN MIND** that this code is very, VERY old, my way of both thinking and coding has changed a lot and I am not deleting all this NOT because I find this code or this project good, BUT because I love the memories. I know can do much better :)
### You want to develop something similar
Wow, cool! But this highly likely means you are in the wrong place. At least, if you want to use any part of these project, you are, of course, allowed to, as stated in the LICENSE, but, one more time, the code is bad. If you want to ask something or get me involved in some way, feel free to contact me (e-mail, Telegram, VK, ...), but I am not sure what I can be useful for to you ¯\\\_(ツ)\_/¯
### You want to use the project
Well... I disrecommend this :). Firstly, this project **WAS NOT** even **FINISHED**. I have stopped developing it when I understood that neither I nor any other member of [my CTF team](https://ctftime.org/team/109148) needs this manager. Secondly, the code in this project is very bad, hard to support, hard to run in any conditions even a bit different from the conditions I was developing it in.
