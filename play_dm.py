#!/usr/bin/env python3
import os
import sys
import time
from dotenv import load_dotenv
load_dotenv()

from generator.gpt2.gpt2_generator import *
from generator.human_dm import *
from play import *
from story.story_manager import *
from story.utils import *
client = discord.Client()

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


class AIPlayer:
    def __init__(self, generator):
        self.generator = generator

    def get_action(self, prompt):
        return self.generator.generate_raw(prompt)


async def play_dm():

    await message.channel.send("Initializing AI Dungeon DM Mode")
    generator = GPT2Generator(temperature=0.9)

    story_manager = UnconstrainedStoryManager(HumanDM())
    context, prompt = select_game()
    await message.channel.send(context + prompt)
    story_manager.start_new_story(prompt, context=context, upload_story=False)

    player = AIPlayer(generator)

    while True:
        action_prompt = story_manager.story_context() + "What do you do next? \n> You"
        action = player.get_action(action_prompt)
        print("\n******DEBUG FULL ACTION*******")
        await message.channel.send(action)
        print("******END DEBUG******\n")
        action = action.split("\n")[0]
        punc = action.rfind(".")
        if punc > 0:
            action = action[: punc + 1]
        shown_action = "> You" + action
        await message.channel.send(second_to_first_person(shown_action))
        story_manager.act(action)

@client.event
async def on_ready():
  print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):

  if message.content.startswith('$playai'):
    await play_dm(message)
