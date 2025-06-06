from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement
from speech_to_text import SpeechToText
from transformers import pipeline 
from google import genai
from google.genai import types
import time 
import re 
from speech_recognition import AudioData

import pyttsx3
import cv2 as cv
import numpy as np
import wave
import os
import time
import audioop
from pydub import AudioSegment


@inlineCallbacks
def main(session, details):
    yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # default is ~200
    file_path = "output.wav"
    text = "Hello, how are you today?"
    engine.save_to_file(text, file_path)
    engine.say(text)
    engine.runAndWait()
    audio = AudioSegment.from_wav(file_path)
    audio.export("output.mp3", format="mp3")


    with wave.open(file_path, 'rb') as wav_file:
        sample_rate = wav_file.getframerate()          # Should be 44100 Hz
        num_channels = wav_file.getnchannels()         # Make sure it's stereo (2)
        raw_data = wav_file.readframes(wav_file.getnframes())
    print(f"sample rate: {sample_rate}, num_channels: {num_channels}")
    if num_channels == 1:
        raw_data = audioop.tostereo(raw_data, 2, 1, 1) #this does not change it to stereo successfully

    #audio = raw_data
    #yield session.call("rom.actuator.audio.volume", volume = 50)
    print(f"num_channels: {num_channels}, should be 2 now")
    #yield session.call("rom.actuator.audio.play", data = "output.wav", rate = 1600)
    yield session.call("rom.actuator.audio.stream", url = "https://drive.google.com/file/d/1qS7KW5z9rAWCZhdaPT1Lj6NgXxwjPeqj/view?usp=drive_link", sync = False)
    #https://drive.google.com/file/d/1qS7KW5z9rAWCZhdaPT1Lj6NgXxwjPeqj/view?usp=drive_link
    yield sleep(30)
    print("code ran all the way")
    session.leave()

wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.683ef4b69827d41c07336acb",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])