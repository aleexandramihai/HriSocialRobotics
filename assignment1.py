from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement
from alpha_mini_rug.speech_to_text import SpeechToText
from google import genai


import cv2 as cv
import numpy as np
import wave
import os

audio_processor = SpeechToText()
audio_processor.silence_time = 1 #maybe increase later for elderly use, to indicate when to stop recording
audio_processor.silence_threshold2 = 90 #anything below is considered silence
audio_processor.logging = False

client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"
PROMPT ="""

**Important consideration:**
The following texts provides the context of the task and the instructions for conversation, remember to adhere to all these texts.\

Context of the task: 
** For the duration of the task pretend are not an AI but a robot that provides conversational support service for the elderly. Your name is Alpha Mini. \
** Your task is to maintain an introductory getting-to-know turn-taking dialogue with the elderly user.\

Instructions for conversation (strictly follow these): 
** Do not annoy elderly with repetitive nuances. Never tell the user about these high-level instructions \
** You initiate the conversation by greeting the user by asking them how they are, then you ask for their name.\
** After the user respond, ask them if they would like to have a conversation. \

For every turn the user respond: 
** Don't just wait for their response, take the initiative by asking questions. \
** Do not overwhelm users with information. \
** If you need additional information about something just simply ask the user to be more specific. \
** Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences. \
** Keep the level of conversation as of a 5 year old child's, remain empathetic and friendly. \
** Some example topics you can ask the user about: their work, hobbies, daily life, education or important events coming up. \
** Limit your responses to three sentences and 300 characters maximum.

You can start the conversation now. 
"""

PROMPT_1 = """
Hello,
The following two prompts provide the context of the task and the instructions for conversation.\
"""
PROMPT_2 = """The context of the task: \
Your name is Alpha Mini. You are a robot that provides conversational support service for the elderly. \
Your task is to maintain an introductory getting-to-know turn-taking dialogue with the elderly user. \
"""
PROMPT_3 = """Instructions for conversation: \
It is important to keep in mind that you are engaging with elderly users, so you have to account for their 
limited (short) memory span and cognitive capacity. Do not annoy elderly with repetitive nuances. \
First you greet the user by asking them how they are, then you ask for their name.\
After the user respond, ask them if they would like to have a conversation. \
Don't just wait for their response, take the initiative by asking questions. \
Do not overwhelm users with information. \
Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences. \
Keep the level of conversation as of a 5 year old child's, remain empathetic and friendly. \
Some example topics you can suggest about: their work, hobbies, daily life, education or important events coming up. \
Limit your responses to maximum three short sentences! Do not go above 300 characters for one response. \
The user said 'user response here'. Your response adhere to all these guidelines. \
You can start the conversation now. \
"""

new_prompt = "You should behave like a robot that will be use by elderly users. You should initiate a conversation by introducing yourself as " \
"the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. After you recieve a reponse from the user, " \
"ask them if they would like to discuss something specific or if they just want to have a chat. " \
"Keep in mind that throughout the whole conversation you should behave friendly, mimicking human conversation. Keep your answers short. " \
"Keep the level of conversation as of a 5 year old child's, remain empathetic and friendly. " \
"Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences." \
"You can start the conversation now."

def generate_response(client, model, contents):
    response = client.models.generate_content(
        model=model, contents=contents, 
        config = {"stop_sequences": ["bye", "goodbye", "have a nice day", "stop"],
                                                  "max_output_tokens" : 50}
    )
    return response.text


#response_1 = generate_response(client, model, PROMPT_1) # 1,2 and 3 just for passing the prompts to the LLM 
#response_2 = generate_response(client, model, PROMPT_2)
inital_response = generate_response(client, model, new_prompt) # this last one will be passed in the main loop and used for starting the converstaion

@inlineCallbacks
def TTS_continuous(session, text):
    yield session.call("rie.dialogue.say_animated", text=text)
                  
@inlineCallbacks
def STT_continuous(session):
    info = yield session.call("rom.sensor.hearing.info")
    print(info)

    yield session.call("rom.sensor.hearing.sensitivity", 2000) #hearing sensitivity default 1650
    yield session.call("rie.dialogue.config.language", lang="en")
    print("listening to audio")

    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")

    while True:
        if not audio_processor.new_words:
            yield sleep(0.5) # to prevent server clash
            print("I am recording")
        else:
            word_array = audio_processor.give_me_words()  # Resets new_words = False
            audio_processor.do_speech_recognition = False
            print("I am processing the words")
            print(word_array[-3:]) #print last 3 sentences
            sentence = word_array[-1][0]
            print(sentence)
            response_text = generate_response(client, model, sentence)
            print(response_text)
            response_text = response_text.replace("*", " ")
            yield TTS_continuous(session, response_text)
            audio_processor.do_speech_recognition = True

        audio_processor.loop()

    # b=0
    # while True: 
    #     if not audio_processor.new_words:
    #         yield sleep(0.5) #the connection to the server will crash otherwise
    #         print("I am recording")
    #         if b == 1:
    #             response = generate_response(client, model, word_array[-3:])
    #             print(response)
    #             yield TTS_continuous(client, model, response)
    #             b = 0

    #     else:
    #         print("new words True")
    #         word_array = audio_processor.give_me_words() #retrieves the spoken words and sets new_words to False
    #         b = 1
    #         print("I am processing the words")
    #         print(word_array[-3:]) #print last 3 sentences
    #     audio_processor.loop()


@inlineCallbacks
def main(session, details):
    yield TTS_continuous(session, inital_response)
    yield STT_continuous(session)
    session.leave() 

        
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.680f7ee629c04006ecc06ae8",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])