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
audio_processor.silence_time = 0.5
audio_processor.silence_threshold2 = 100

audio_processor.logging = False

def generate_response(contents):
    client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents="Explain how AI works in a few words"
    )
    print(response.text)

 
@inlineCallbacks
def main(session, details):

    yield STT_continuous(session)
    session.leave() 
    generate_response("Explain how AI works in a few words")

                  
@inlineCallbacks
def STT_continuous(session):
    info = yield session.call("rom.sensor.hearing.info")
    print(info)

    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")
    yield session.call("rie.dialogue.say_animated", text="Say something")
    print("listening to audio")

    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")

    while True: 
        if not audio_processor.new_words:
            yield sleep(0.5)
            print("I am recording")
        else:
            word_array = audio_processor.give_me_words()
            print("I am processing the words")
            print(word_array[-3:])
        audio_processor.loop()
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.6808d93a29c04006ecc04b7b",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])