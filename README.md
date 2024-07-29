# discord-jeopardy-2

A bot for Discord using [discord.py](https://github.com/Rapptz/discord.py).

Play Jeopardy! from the comfort of a Discord chat.

```markdown
Use the command `/clue` or mention the bot followed by the word 'clue'
You must phrase your answers like questions, for example:
- what's bear
- who's houdini?
- whats up bro
If you give up, wait for the time to run out or say 'skip clue'
For more information use the help command with `faq` or `clue`
```

To host the bot yourself:
- Install discord.py (or use pipenv with the repository's Pipfile)
- Provide values to the environment variables:
  - TEST_SERVER_ID (optional, runs [sync](https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.app_commands.CommandTree.sync) with `guild=TEST_SERVER_ID`)
  - TOKEN (**required**, this is your bot's token from your Discord Applications)
  - CLEAR_ALL_COMMANDS (optional, if set to to `TRUE` runs [clear_commands](https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.app_commands.CommandTree.clear_commands) for all guilds)
  - SYNC_ALL_COMMANDS (optional, use at least once to sync application commands, if set to `TRUE` runs [sync](https://discordpy.readthedocs.io/en/latest/interactions/api.html#discord.app_commands.CommandTree.sync) for all guilds)

Uses [jservice.xyz](https://jservice.xyz/) API for Jeopardy! clues.
