#!/usr/bin/env python3

#
# Discord API Reference: https://discordpy.readthedocs.io/en/latest/ext/commands/api.html
#
import os, sys, random, time
import discord
import json
import pathlib
# make requests out to the web
import requests
# used to load the .env file
from dotenv import load_dotenv
load_dotenv()

from generator.gpt2.gpt2_generator import *
from story import grammars
from story.story_manager import *
from story.utils import *

client = discord.Client()

os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

def random_story(story_data):
    # random setting
    settings = story_data["settings"].keys()
    n_settings = len(settings)
    n_settings = 2
    rand_n = random.randint(0, n_settings - 1)
    for i, setting in enumerate(settings):
        if i == rand_n:
            setting_key = setting

    # random character
    characters = story_data["settings"][setting_key]["characters"]
    n_characters = len(characters)
    rand_n = random.randint(0, n_characters - 1)
    for i, character in enumerate(characters):
        if i == rand_n:
            character_key = character

    # random name
    name = grammars.direct(setting_key, "character_name")

    return setting_key, character_key, name, None, None


async def select_game(message):

    with open(YAML_FILE, "r") as stream:
        data = yaml.safe_load(stream)


    return random_story(data)

def get_curated_exposition(
    setting_key, character_key, name, character, setting_description
):
    name_token = "<NAME>"
    try:
        context = grammars.generate(setting_key, character_key, "context") + "\n\n"
        context = context.replace(name_token, name)
        prompt = grammars.generate(setting_key, character_key, "prompt")
        prompt = prompt.replace(name_token, name)
    except:
        context = (
            "You are "
            + name
            + ", a "
            + character_key
            + " "
            + setting_description
            + "You have a "
            + character["item1"]
            + " and a "
            + character["item2"]
            + ". "
        )
        prompt_num = np.random.randint(0, len(character["prompts"]))
        prompt = character["prompts"][prompt_num]

    return context, prompt


def instructions():
    text = "\nAI Dungeon 2 Instructions:"
    text += '\n Enter actions starting with a verb ex. "go to the tavern" or "attack the orc."'
    text += '\n To speak enter \'say "(thing you want to say)"\' or just "(thing you want to say)" '
    return text

async def start(message):

    upload_story = False
    await message.channel.send("\nInitializing AI Dungeon! (This might take a few minutes)\n")

    generator = GPT2Generator(force_cpu=True)
    generator.censor = False
    story_manager = UnconstrainedStoryManager(generator)

    story_manager.story = None

    (   
        setting_key,
        character_key,
        name,
        character,
        setting_description,
    ) = await select_game(message)

    context, prompt = get_curated_exposition(
            setting_key, character_key, name, character, setting_description
        )

    await message.channel.send(instructions())
    await message.channel.send("\nGenerating story...")

    result = story_manager.start_new_story(
        prompt, context=context, upload_story=upload_story
    )

    await message.channel.send(result)
    id = story_manager.story.save_to_storage()

    return id

async def play(saveId, action, message):

    if(saveId is None):
        await message.channel.send("Your previous game ended. Starting new game.")
        return await start(message)

    generator = GPT2Generator(force_cpu=True)
    generator.censor = False
    story_manager = UnconstrainedStoryManager(generator)
    story_manager.story = None

    result = story_manager.load_new_story(
                    saveId, upload_story=False
                )

    if action == "":
        action = ""
        result = story_manager.act(action)
        if result != "":
            await message.channel.send(result)

    elif action[0] == '"':
        action = "You say " + action
        await message.channel.send(action)

    else:
        action = action.strip()

        if "you" not in action[:6].lower() and "I" not in action[:6]:
            action = action[0].lower() + action[1:]
            action = "You " + action

        if action[-1] not in [".", "?", "!"]:
            action = action + "."

        action = first_to_second_person(action)

        action = "\n> " + action + "\n"

    result = "\n" + story_manager.act(action)
    if len(story_manager.story.results) >= 2:
        similarity = get_similarity(
            story_manager.story.results[-1], story_manager.story.results[-2]
        )
        if similarity > 0.9:
            story_manager.story.actions = story_manager.story.actions[:-1]
            story_manager.story.results = story_manager.story.results[:-1]
            await message.channel.send(
                "Woops that action caused the model to start looping. Try a different action to prevent that."
            )

    if player_won(result):
        await message.channel.send(result + "\n CONGRATS YOU WIN")
        story_manager.story.get_rating()
        return None
    elif player_died(result):
        await message.channel.send(result)
        await message.channel.send("YOU DIED. GAME OVER")
        story_manager.story.get_rating()
        return None

    else:
        if result != "":
            await message.channel.send(result)

    id = story_manager.story.save_to_storage()
    return id

cmd = 'initial'

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message): 

    userState = {'saveId':''}

    userStateFile = './user-state/{0.id}-state.json'.format(message.author)
    file = pathlib.Path(userStateFile)
    if file.exists():
        with open(userStateFile) as f:
            userState = json.load(f)

    print(f"User State: {json.dumps(userState)}")

    cmd = message.content
    if message.content.startswith(';'):
        cmd = message.content.split(';')[1]
        print(f"Command passed in: {cmd}")

        if(cmd == 'playai'):
            id = await start(message)
        else:
            id = await play(userState['saveId'], cmd, message)

        userState['saveId'] =  id

        with open(userStateFile, 'w') as json_file:
            json.dump(userState, json_file)

client.run(os.getenv('BOT_TOKEN'))

