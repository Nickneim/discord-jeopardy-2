# from discord import app_commands
import discord
from discord.utils import escape_markdown
from discord.ext import commands
from typing import Any, Coroutine, Optional

from asyncio import TimeoutError
from random import randint

from difflib import SequenceMatcher
from datetime import datetime

import re
import logging


TAG_RE = re.compile(r'<[^>]*>')
BR_TAG_RE = re.compile(r'<br \/>')
BETWEEN_PARENTHESES = re.compile(r'\([^\)]*\)')
PARENTHESES = re.compile(r'[()]')
ANSWER_START_RE = re.compile(r"^(?:wh(?:at|ere|o)(?: is|'s|s| are)|que es|qué es) +")
ANSWER_STARTS = ("what is ", "what's ", "whats ", "what are ",
                 "where is ", "where's ", "wheres " "where are ",
                 "who is ", "who's ", "whos ", "who are ",
                 "que es ", "qué es ",
                 "skip clue")

CATEGORY_AMOUNT = 45374
CLUE_AMOUNT = 402824
CLUE_TIME_LIMIT = 52.5

J_ARCHIVE_RE = re.compile(r'j\-archive')

JSERVICE = "https://jservice.xyz/"



async def jservice_get_json(session, path, params={}):
    logging.info(path)
    logging.info(params)
    async with session.get(JSERVICE + path, params=params) as r:
        if r.status == 200:
            js = await r.json()
            return js
        else:
            return None


def is_link_clue(clue):
    """Clue has a j-archive link"""
    return J_ARCHIVE_RE.search(clue['question'])


def is_valid_clue(clue, allow_link=False):
    return (not clue['invalidCount']
            and clue['question']
            and clue['answer']
            and (allow_link or not is_link_clue(clue))
            )

def get_possible_answers(clue):
    answer = TAG_RE.sub('', clue['answer']).strip().lower()
    # if the answer is something like "(John) Smith", we allow "Smith" and "John Smith"
    if answer[0] == "(":
        possible_answers = [BETWEEN_PARENTHESES.sub('', answer),
                                    PARENTHESES.sub('', answer)]
    elif answer[-1] == ")":
        start = answer.find("(")
        # if the answer is something like "John (or Johnny)", we allow "John" and "Johnny"
        if answer[start+1:].startswith("or "):
            possible_answers = [answer[:start], answer[start+4:-1]]
        # if the answer is something like "John (Smith)", we allow "John" and "John Smith"
        else:
            possible_answers = [BETWEEN_PARENTHESES.sub('', answer),
                                        PARENTHESES.sub('', answer)]
    else:
    # otherwise we only allow the answer (even if it has parentheses in the middle)
        possible_answers = [answer]
    for i, answer in enumerate(possible_answers):
        try:
            integer_answer = int(answer)
        except ValueError:
            continue
        else:
            possible_answers[i] = integer_answer
    return possible_answers


def question_to_str(clue):
    return (f"The category is **{clue['category']['title']}** for ${clue['value']}: " +
            f"`{clue['id']}` ({clue['game']['aired'][5:7]}/{clue['game']['aired'][2:4]})\n```md\n{clue['question']}```"
            )



def is_correct_answer(answer, possible_answers, similarity_ratio=0.65):
    close_answer = False
    for correct_answer in possible_answers:
        # if the correct answer is a number, we only allow this exact number
        if isinstance(correct_answer, int):
            try:
                if int(answer) == correct_answer:
                    return True
            except ValueError:
                pass
        # otherwise we use SequenceMatcher to check if the string is "similar"
        elif similarity_ratio <= SequenceMatcher(None, correct_answer,
                                                    answer).ratio():
            return True
        # otherwise we check if all the words in the user's answer are in the correct answer
        # later we'll make sure this makes the answer similar enough
        elif not close_answer:
            possible_answer_split = re.split(r"\W+", answer)
            correct_answer_split = re.split(r"\W+", correct_answer)
            if any((word not in correct_answer_split for word in possible_answer_split)):
                continue
            close_answer = True

    if close_answer:
        for correct_answer in possible_answers:
            possible_answer_split = re.split(r"\W+", answer)
            correct_answer_split = re.split(r"\W+", correct_answer)
            if any((word not in correct_answer_split for word in possible_answer_split)):
                continue
            # we create a generous answer using the words used by the user (valga la redundancia)
            possible_answer = " ".join((word for word in correct_answer_split if word in possible_answer_split))
            if similarity_ratio <= SequenceMatcher(None, correct_answer, 
                                                    possible_answer).ratio():
                return True
        # if we've reached this point, the user's answer is close but still needs more words
        return None
    else:
        return False

class NextClueButtonView(discord.ui.View):
    def __init__(self, *, timeout=60, parent : discord.Message, jeopardy_cog: commands.Cog, ctx: commands.Context):
        self.parent = parent
        self.jeopardy_cog = jeopardy_cog
        self.ctx = ctx
        super().__init__(timeout=timeout)

    async def on_timeout(self) -> Coroutine[Any, Any, None]:
        self.clear_items()
        await self.parent.edit(view=self)
        return await super().on_timeout()

    @discord.ui.button(emoji="🔁", style=discord.ButtonStyle.primary)
    async def next_clue_button(self, interaction:discord.Interaction, button:discord.ui.Button):
        self.clear_items()            
        await interaction.response.edit_message(view=self)
        self.ctx.repeated_clue = True
        await self.jeopardy_cog.clue_command.invoke(self.ctx)

    

class JeopardyCog(commands.Cog, name='Jeopardy'):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot

    # If I use HybridCommand, invoke doesn't work inside NextClueButtonView when
    # the user uses the application command (/clue). No idea why.
    # The workaround is to have AppCommand and Command separate, and make
    # AppCommand do nothing else but invoke Command. This way, in practice we're
    # only using Command (which works fine when invoked from NextClueButtonView)
    @discord.app_commands.command(name="clue")
    async def clue_app_command(self, interaction: discord.Interaction, clue_id: Optional[int] = None) -> None:
        """Gets a random clue or a clue with a specific id"""
        ctx : commands.Context = await commands.Context.from_interaction(interaction)
        if clue_id is not None:
            ctx.view.__init__(str(clue_id))
        await self.clue_command.invoke(ctx)

    @clue_app_command.error
    async def clue_command_error(self, interaction : discord.Interaction, error : discord.app_commands.AppCommandError):
        if isinstance(error, discord.app_commands.CommandInvokeError):
            if isinstance(error.original, commands.MaxConcurrencyReached):
                return await interaction.response.send_message("There's already an active clue in this channel!", ephemeral=True)
        await interaction.response.send_message("Something went wrong! Try again?")
        raise error

    @commands.command(name="clue")
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    async def clue_command(self, ctx: commands.Context, clue_id: Optional[int] = None) -> None:
        """Gets a random clue or a clue with a specific id"""

        # Get Clue
        if clue_id is None:
            for _ in range(20):
                # we manually search for a specific random clue (since api/random-clue is slower)
                clue_id = randint(1, CLUE_AMOUNT)
                clue = await jservice_get_json(self.bot.web_client, f"api/clues/{clue_id}")
                if not clue or not is_valid_clue(clue):
                    clue = None
                    continue
                break
            if not clue or not is_valid_clue(clue):
                return await ctx.send("Failed to get a random clue, maybe the service is down?")
        else:
            clue = await jservice_get_json(self.bot.web_client, f"api/clues/{clue_id}")
            if not clue:
                return await ctx.send("Failed to get a clue with that id.")
            if not is_valid_clue(clue, allow_link=True):
                return await ctx.send("That doesn't seem to be a valid clue.")
        
        # Process Clue
        clue['question'] = BR_TAG_RE.sub('\n', clue['question'])
        clue['question'] = TAG_RE.sub('', clue['question'])
        question_text = question_to_str(clue)
        # 'question' will be our main message where we add the next question button
        if hasattr(ctx, 'repeated_clue'):
            original_question = await ctx.channel.send(question_text)
        else:
            original_question = await ctx.send(question_text)
        question = original_question
        possible_answers = get_possible_answers(clue)

        # Set up valid answer function
        def is_valid_answer(message):
            return (message.channel.id == ctx.channel.id and
                    message.content.lower().startswith(ANSWER_STARTS))


        question_start = datetime.utcnow()
        remaining_time = max(0.5, CLUE_TIME_LIMIT - (datetime.utcnow() - question_start).total_seconds())
        while remaining_time > 0:
            remaining_time = max(0.5, CLUE_TIME_LIMIT - (datetime.utcnow() - question_start).total_seconds())

            # Get possible answer
            try:
                answer : discord.Message = await self.bot.wait_for('message', timeout=remaining_time,
                                                 check=is_valid_answer)
            except TimeoutError:
                question = await original_question.reply("Time's up! The correct response was "
                                            f"**{clue['answer']}**.", mention_author=False)
                break


            # Check answer
            answer_text = answer.content.lower()
            if answer_text.startswith("skip clue"):
                question = await answer.reply("Ok.", mention_author=False)
                break
            # extract the answer from the message text
            answer_text = ANSWER_START_RE.sub('', answer_text, 1)
            if answer_text.endswith('?') and answer_text[:-1].strip():
                answer_text = answer_text[:-1].strip()
            # check answer
            result = is_correct_answer(answer_text, possible_answers)
            if result:
                question = await answer.reply("That's correct, {}. The correct response was **{}**.".format(
                                 escape_markdown(answer.author.display_name), clue['answer']), mention_author=False)
                break
            elif result is None:
                question = await answer.reply("Be more specific, {}.".format(
                                          escape_markdown(answer.author.display_name)), mention_author=False)
            else:
                question = await answer.reply(f"That's incorrect, {escape_markdown(answer.author.display_name)}.", mention_author=False)

        await question.edit(view=NextClueButtonView(parent=question, jeopardy_cog=self, ctx=ctx))

    @clue_command.error
    async def clue_command_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            return await ctx.reply("There's already an active clue in this channel!", mention_author=False)
        
        await ctx.send("Something went wrong! Try again?")
        raise error

async def setup(bot):
    await bot.add_cog(JeopardyCog(bot))