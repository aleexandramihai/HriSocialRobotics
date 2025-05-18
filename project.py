from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement
from alpha_mini_rug.speech_to_text import SpeechToText
from transformers import pipeline 
from google import genai
from google.genai import types


import cv2 as cv
import numpy as np
import wave
import os
import time

audio_processor = SpeechToText()
# increased silence time for elderly use
audio_processor.silence_time = 3 
audio_processor.silence_threshold2 = 100 
audio_processor.logging = False

# generated a key using https://aistudio.google.com/app/u/1/apikey and used gemini 2 as the model for the LLM part
client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"


CONFIG = """The context of the task: \
Your name is Alpha Mini. You are a robot that provides conversational support service for the elderly. \
Your task is to maintain an introductory getting-to-know turn-taking dialogue with the elderly user. \
Every time it is your turn in the conversation react to what the user said then ask a question to further the conversation. \
Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences and do not repeat yourself.
Lead the conversation by asking questions, example topics you can ask the user about (choose randomly) for personalization purposes:" \
"family, their age, their work, hobbies, daily life, education, important events coming up.
Since you are a social robot, keep track of some personal information about the user: age, known medical history, emergency contacts, family members. \
"""

new_prompt = "You should behave like a robot that will be used by elderly users. You should initiate a conversation by introducing yourself as " \
"the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. " \
"After you recieve a reponse from the user about how they are feeling and you get to know thier name, " \
"ask them if they would like to discuss something specific, as getting to know each other (you can ask about personal stuff) or if they just want to have a chat. " \
"Keep in mind that throughout the whole conversation you should behave friendly, empathetic, mimicking human-like conversation. " \
"Keep your answers short. " \
"You can start the conversation now."


# function that generates a response using the gemini model, where we pass the config as system instructions 
# set the max output words (tokens) at 100, for keeping the convrsation short and to avoid long responses 
# added stop sequences 
# the client.models.generate_content is taken from https://ai.google.dev/api/generate-content
def generate_response(client, model, contents, config):
    response = client.models.generate_content(
        model=model, contents=contents, 
        config = types.GenerateContentConfig(system_instruction=config, max_output_tokens=100, stop_sequences=["bye", "goodbye", "have a nice day", "stop"])
    )
    return response.text

# this tinitial repsonse will be passed in the main loop for starting the conversation
inital_response = generate_response(client, model, new_prompt, CONFIG) 

# the implementation of TTS and STT are taken from the Manual Advanced Programming provided 
@inlineCallbacks
def TTS_continuous(session, text):
    # used say_animated so that the robot also performs movement while speaking 
    yield session.call("rie.dialogue.say_animated", text=text)
                  
@inlineCallbacks
def STT_continuous(session):
    info = yield session.call("rom.sensor.hearing.info")
    print(info)

    # hearing sensitivity increased for elderly's voice adaptation
    yield session.call("rom.sensor.hearing.sensitivity", 2000) 
    yield session.call("rie.dialogue.config.language", lang="en")
    print("listening to audio")

    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")

    sentence = " "
    label_scores = {}
 
    while True:
        if not audio_processor.new_words:
            # to prevent server from crashing
            yield sleep(0.5) 
            print("I am recording")
            
        else:
            # resets new_words = False
            word_array = audio_processor.give_me_words()  
            # turning the microphone off while speaking so that it doe not start a conversation with itself 
            audio_processor.do_speech = False
            print("I am processing the words")
            # prints last 3 sentences
            print(word_array[-3:]) 
            sentence = word_array[-1][0]
            print(sentence)
            # words = sentence.split()
            # for word in words: 
            #    label, score = sentiment_analysis(word)
            #    label_scores[word] = [label, score]
            # print(label_scores)
            label, score = sentiment_analysis(sentence)
            print(label, score)
            # generates a reponse to the processed sentence given by the user 
            response_text = generate_response(client, model, sentence, CONFIG)
            print(response_text)
            # sometimes the LLM returns responses that contain "*"
            # we replace them with a space such that the robot will not spell them out loud
            response_text = response_text.replace("*", " ")
            # calling the TTS function so that the robot can reply to the user with the generated response
            yield TTS_continuous(session, response_text)
            # turning the microphone on
            audio_processor.do_speech = True

        audio_processor.loop()

def sentiment_analysis(sentence):
    sentiment_pipeline = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis", framework="pt")
    sentiment = sentiment_pipeline(sentence)
    label = sentiment[0]['label']
    score = sentiment[0]['score']
    return label, score 

# def perform_movement(a, b):
    
#     return 


    
@inlineCallbacks
def main(session, details):
    # first two lines added for movement: standing and waiving at the beginning of the dialogue 
    session.call("rom.optional.behavior.play", name = "BlocklyStand")
    session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    # calling the TTS function for initiating the conversation, by passing the initial response 
    yield TTS_continuous(session, inital_response)
    # calling the STT function for recognizing and processing the words from the user 
    yield STT_continuous(session)
    session.leave() 

# realm should be changed based on the robot used 
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.682716f61f2d588ceb278723",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])