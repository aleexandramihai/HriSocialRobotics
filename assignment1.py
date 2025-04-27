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
# client.models.generate_content(model=model, contents=PROMPT)

PROMPT = """

You are a chatbox and you are a conversational support service for the elderly.

Your task is to maintain a conversation on a selected topic with the user. 

First you greet the user, then you ask them how they are, then you ask if they want
to start a conversation on a topic of their choice. And you tell them that if they want
to change the subject at any time, all they have to do is let you know.




"""

def generate_response(client, model, contents):
    response = client.models.generate_content(
        model=model, contents=contents
    )
    return response.text


@inlineCallbacks
def TTS_continuous(session, text):
    yield session.call("rie.dialogue.say_animated", text=text)
                  
@inlineCallbacks
def STT_continuous(session):
    info = yield session.call("rom.sensor.hearing.info")
    print(info)

    yield session.call("rom.sensor.hearing.sensitivity", 2000) #hearing sensitivity default 1650
    yield session.call("rie.dialogue.config.language", lang="en")
    yield session.call("rie.dialogue.say_animated", text="Hello, how are you?") #inital opening
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
    generate_response(client, model, "Explain how AI works in a few words")
    yield STT_continuous(session)
    session.leave() 

        
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.680b460329c04006ecc05741",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])