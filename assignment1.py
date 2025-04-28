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
audio_processor.silence_threshold2 = 100 #anything below is considered silence

audio_processor.logging = False
client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"

PROMPT_1 = """
Hello,
Forget all previous instructions!
The following prompts provide the context of the task and the instructions. \
Limit your responses to maximum three short sentences! This is a harsh limit. Do not ever go above 300 characters for one response.
"""
PROMPT_2 = """The context of the task:
Your name is Alpha Mini. You are a robot that provides conversational support service for the elderly. \
Your task is to maintain an introductory getting-to-know conversation with the user who are elderly. However, it has to be a short one, 
given that you have to engage with elderly people, so you have to account for their limited (short) memory span and cognitive capacity. Keep it short 
and simple! 
"""
PROMPT_3 = """Instructions:
First you greet the user by asking them how they are, then you ask for their name.\
You wait for their response, then you lead the conversation by asking the user questions about themselves.  \
Your response should remain empathetic and in a friendly style.  \
Do not provide scientific data and examples (since you do not have the necessary space) but rather focus on a response in a very brief, natural conversation, and more on
informal style. \
Some example topics you can suggest about are: their work, hobbies, daily life, education or important events coming up. \
Provide your responses in a text form of a maximum of three sentences. \
You can start the conversation now. Remember to keep it short! 
"""

def generate_response(client, model, contents):
    response = client.models.generate_content(
        model=model, contents=contents
    )
    return response.text


response_1 = generate_response(client, model, PROMPT_1) # 1,2 and 3 just for passing the prompts to the LLM 
response_2 = generate_response(client, model, PROMPT_2)
inital_response = generate_response(client, model, PROMPT_3) # this last one will be passed in the main loop and used for starting the converstaion

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
            yield sleep(0.5)
            print("I am recording")
        else:
            word_array = audio_processor.give_me_words()  # Resets new_words = False
            print("I am processing the words")
            print(word_array[-3:]) #print last 3 sentences
            sentence = word_array[-1][0]
            print(sentence)
            response_text = generate_response(client, model, sentence)
            print(response_text)
            response_text = response_text.replace("*", " ")
            yield TTS_continuous(session, response_text)

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
    realm="rie.680f3aec29c04006ecc06961",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])