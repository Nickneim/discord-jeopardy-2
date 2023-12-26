import discord
from discord.ext import commands


FAQ = """
**How does the bot check that the answer is correct?**
If the answer is a number (like 1984), you must write it exactly this way.
If the answer is a word or a sentence, the bot checks for 'similarity' between your answer and the correct answer.
This similarity is not semantic, so 'stone' is not similar to 'rock'.
Instead it tries to match string patterns, so it's closer to a phone's autocorrect.
**Why did the bot allow a clearly incorrect response?**
See above, and also it's very generous so I don't get too many complaints.
**What does 'Be more specific' mean?**
The correct answer contains all the words in your response, but you're still missing some.
For example, the answer is "The Matrix" and you just replied "What's The?"
**Where does the bot get all the clues?**
It uses this API: https://jservice.xyz/
**The bot is broken! Help!**
Just mention me or DM me. (`cool_nico`)
**Why is the avatar Regis Philbin?**
No, it isn't.
"""

HELP = """
JeopardyBot is a Bot to play Jeopardy! created by `cool_nico`
Use the command `/clue` or mention the bot followed by the word 'clue'
You must phrase your answers like questions, for example:
- what's bear
- who's houdini?
- whats up bro
If you give up, wait for the time to run out or say 'skip clue'
For more information use the help command with `faq` or `clue`
"""


class HelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        await self.get_destination().send(embed=discord.Embed(description=HELP))

    def command_not_found(self, string: str, /) -> str:
        if string.strip().lower() == "faq":
            return FAQ
        return f'No command called "{string}" found.'

    async def send_group_help(self, group):
        return await self.get_destination().send(self.command_not_found(group.qualified_name))

    async def send_command_help(self, cmd):
        desc = f"```\n{cmd.name} {cmd.signature}\n{cmd.help or cmd.short_doc}```"
        await self.get_destination().send(embed=discord.Embed(description=desc))

    async def send_cog_help(self, cog):
        return await self.get_destination().send(self.command_not_found(cog.qualified_name))

class HelpCog(commands.Cog, name='Help'):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot


    @discord.app_commands.command(name="help")
    async def help_command(self, interaction: discord.Interaction, /, *, command: str=None):
        """Shows this message"""

        if command is None:
            command = ""
        response = None
        embed = None
        command = command.strip()
        if not command:
            embed = discord.Embed(description=HELP)
        elif self.bot.get_command(command):
            cmd = self.bot.get_command(command)
            embed = discord.Embed(description=f"```\n{cmd.name} {cmd.signature}\n{cmd.help or cmd.short_doc}```")
        else:
            response = self.bot.help_command.command_not_found(command)

        await interaction.response.send_message(response, embed=embed, ephemeral=True)

async def setup(bot):
    bot._default_help_command = bot.help_command
    bot.help_command = HelpCommand()
    await bot.add_cog(HelpCog(bot))


async def teardown(bot):
    bot.help_command = bot._default_help_command