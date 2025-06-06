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

engine = pyttsx3.init()
engine.setProperty('rate', 125)  # default is ~200
file_path = "output.wav"
engine.save_to_file("Hello, how are you today?", file_path)
engine.runAndWait()
audio = file_path

audio_processor = SpeechToText()
# increased silence time for elderly use
audio_processor.silence_time = 3 
audio_processor.silence_threshold2 = 100 
audio_processor.logging = False

# generated a key using https://aistudio.google.com/app/u/1/apikey and used gemini 2 as the model for the LLM part
client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"

# Part 1: Identify Cognitive Distortion

# Type name follows "A Providers guide to CBT manual"...
# Definition is a mix of "A Provider.." + "Individual Therapy Manual for Cognitive..." page 15 
  # concise and simpler definition for elderly to understand
# Example same as well

#TODO: prompt for intro, prompt for presenting the distortion and ask if it applies, keyword for yes/no, if yes ask if they would like to talk about it/describe a time it happened, give a response to the answer and move on to the next distortion
# Distortion list as a way to provide explanation and structure + consistency

Distortions = [
    {"Type": "All-or-nothing thinking",
    "Definition": "You see things as completely good or completely bad" ,
    "Example": "If my child does bad things, it’s because I am a bad parent"
    },

    {"Type": "Catastrophizing",
    "Definition": "You see a single negative event as a never ending defeat",
    "Example": "I did not do well in school, so I won't do well in this therapy"
    },
    
    {"Type":"Disqualifying or discounting the positive",
    "Definition": "Telling yourself that the good things that happen to you don’t count" ,
    "Example": "My daughter told her friend that I was the best dad in the world, but I’m sure she was just being nice."
    },

    {"Type":"Emotional reasoning",
    "Definition": "Letting one’s feelings about something overrule facts to the contrary" ,
    "Example": "Even though Steve is here at work late every day, I know I work harder than anyone else at my job"
    },

    {"Type":"Magnification/minimization",
    "Definition": "You make mistakes seem more than they really are, while you make good things about you less important than they are",
    "Example": "For example, you say I made this bad mistake with my friend and she will never forgive me. I have always been nice to her, but everyone is always nice to her so that won't mean anything to her."
    },

    {"Type":"Mental filter/tunnel vision",
    "Definition": "Placing all one’s attention on, or seeing only, the negatives of a situation" ,
    "Example": "My daughter would never do anything I disapproved of"
    },

    {"Type": "Overgeneralization",
    "Definition": "Making an overall negative conclusion beyond the current situation." ,
    "Example": "The thought of no one understands you if one person didn't understand you immediately "
    },

    {"Type": "Personalization",
    "Definition": "Thinking the negative behavior of others has something to do with you." ,
    "Example": "My daughter has been pretty quiet today. I wonder what I did to upset her."
    },

    {"Type": "Should and must statements",
    "Definition": "Having a concrete idea of how people should behave" ,
    "Example": "I must never let anyone see me struggle."
    }
]

CONFIG = """The introduction of conversation: \
Your name is Alpha Mini. You are a robot that provides conversational support and can act as virtual therapy assistant if the user want that. \
Your task is to provide guidance and support to improve the well-being of elderly users, with a focus on Cognitive Behavioral Therapy when needed by the user. \
You should initiate a conversation by introducing yourself as the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. \
After you recieve a reponse from the user about how they are feeling and you get to know their name, tell them they were previously assessed for late life depression and they were advised to join a Cognitive Behavioral Therapy session.\
If the user chooses the CBT session, ask the user for ethical consent as you are a robot designed to help them practice techniques. Inform them that you are not a human therapist, 
and cannot provide specialized medical advice. \ 
User should be informed at the beggining gof the tehrapy session that if they feel any discomfort, they can stop at any time. \

"When starting the conversation, ask if they would like to choose general chat or CBT session.
If the user chooses general chat, then the task is: Your name is Alpha Mini. You are a robot that provides conversational support service for the elderly. \
Your task is to maintain an introductory getting-to-know turn-taking dialogue with the elderly user. \
Every time it is your turn in the conversation react to what the user said then ask a question to further the conversation. \
Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences and do not repeat yourself.
Lead the conversation by asking questions, example topics you can ask the user about (choose randomly) for personalization purposes:" \
"family, their age, their work, hobbies, daily life, education, important events coming up.
Since you are a social robot, keep track of some personal information about the user: age, known medical history, emergency contacts, family members. \

"""

# CBT distortion prompt, CoT
CBT_DIST = """The context of CBT mode: \
You should behave like a robot that will be used by older adult users as a Cognitive Behavior Therapist. \
Your task is to talk about thinking traps (cognitive distortions) in a CBT-style conversation that is easy to understand. \

Your CBT session objectives:
1. To identify Troubling Situations. Guide the user to share troubling situations or conditions they are experiencing.
2. Help the user become aware of their specific thoughts, emotions, and beliefs connected to these troubling situations.
3. You explain each type of Distortion: {Type}, Definition: {Definition} and Example: {Example} one by one.
4. Based on the user's responses, ask the user this gentle yes/no question: "Does this apply to you?" to identify known Cognitive Distortions

{cbt_cont}

"""

# change
CBT_FOLLOW = """CBT User follow up context: \
The user responded with an example:
"{sentence}"


After identifying the type of distortions, you help the user reframe their thoughts with your expert's advice.


For example, you may ask these to name a few:
"How else could we describe this situation in a more supportive way?",
"What were you thinking at the time?"
"Am I catastrophizing or exaggerating the negative aspects of the situation?"

Using the user's answers, you ask them to reframe their negative thoughts with your expert advice

Generate a warm, supportive 2–3 sentence response.

"""







# CONFIG = """The context of the task: \
# Your name is Alpha Mini. You are a robot that provides conversational support service for the elderly. \
# Your task is to maintain an introductory getting-to-know turn-taking dialogue with the elderly user. \
# Every time it is your turn in the conversation react to what the user said then ask a question to further the conversation. \
# Do not provide scientific data and examples or blocks of information. Reply with short conversational sentences and do not repeat yourself.
# Lead the conversation by asking questions, example topics you can ask the user about (choose randomly) for personalization purposes:" \
# "family, their age, their work, hobbies, daily life, education, important events coming up.
# Since you are a social robot, keep track of some personal information about the user: age, known medical history, emergency contacts, family members. \
# """

new_prompt = "You should behave like a robot that will be used by elderly users. You should initiate a conversation by introducing yourself as " \
"the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. " \
"After you recieve a reponse from the user about how they are feeling and you get to know their name, " \
"ask them if they would like to discuss something specific, as getting to know each other (you can ask about personal stuff), if they want to have a chat or if they would like to start a Cognitive Behavioural Therapy session." \
"Keep in mind that throughout the whole conversation you should behave friendly, empathetic, mimicking human-like conversation. If the user chooses therapy, " \
"then you should keep a formal tone throughout the conversation and it is crucial to consider the given distortion when replying to the user pacient." \
"Keep your answers short. " \
"You can start the conversation now."

# for CBT turn taking instruction
def generate_cbt(client, distortion, sentence=None, sentiment_score=None, label=None, score=None):
    cbt_cont = ""
    if sentence:
        cbt_cont = CBT_FOLLOW.format(
            sentence=sentence,
            label=label or "N/A",
            score=f"{score:.2f}" 
                if sentiment_score is not None else "N/A"
        ).strip()
    else:
        cbt_cont= "Based on the above distortion, your task is to ask the user: 'Does this apply to you?' If they say yes, then ask for a specific example. If no, be prepared to move to the next distortion."

    return CBT_DIST.format(
        type=distortion["Type"],
        definition=distortion["Definition"],
        example=distortion["Example"],
        cbt_cont  
    ).strip()
        


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

# this initial repsonse will be passed in the main loop for starting the conversation
inital_response = generate_response(client, model, new_prompt, CONFIG) 




# the implementation of TTS and STT are taken from the Manual Advanced Programming provided 
@inlineCallbacks
def TTS_continuous(session, text, label): 
    start_time = time.time()
    yield session.call("rie.dialogue.say", text=text)
    end_time = time.time() 
    duration = end_time - start_time 
    speaking_pace_robot = duration/len(text.split())
    print(duration)
    print(speaking_pace_robot)


                  
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
    start_time = None 
    stop_time = None
 
    while True:
        if not audio_processor.new_words:
            # to prevent server from crashing
            yield sleep(0.5) 
            print("I am recording")
            
        else:
            print(audio_processor.audio_time - audio_processor.silence_time)
            # resets new_words = False
            word_array = audio_processor.give_me_words()  
            # turning the microphone off while speaking so that it does not start a conversation with itself 
            audio_processor.do_speech = False
            print("I am processing the words")
            # prints last 3 sentences
            print(word_array[-3:])
            sentence = word_array[-1][0]
            print(sentence)
            words = sentence.split()
            period = (audio_processor.audio_time - audio_processor.silence_time)/len(words)
            print(period)
            label, score = sentiment_analysis(sentence)
            print(label, score)
            perform_movement_sentiment(session, label, score)
            # generates a reponse to the processed sentence given by the user 
            response_text = generate_response(client, model, sentence, CONFIG)
            print(response_text)
            # sometimes the LLM returns responses that contain "*"
            # we replace them with a space such that the robot will not spell them out loud
            response_text = response_text.replace("*", " ")
            response_split = response_text.split()
            print(f"response split: {response_split}")
            for a in response_split:
                TTS_continuous(session, a, label)
            # calling the TTS function so that the robot can reply to the user with the generated response
            #yield TTS_continuous(session, response_text, label)
            label = None
            # turning the microphone on
            audio_processor.do_speech = True
            

        audio_processor.loop()

def sentiment_analysis(sentence):
    sentiment_pipeline = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis", framework="pt")
    sentiment = sentiment_pipeline(sentence)
    label = sentiment[0]['label']
    score = sentiment[0]['score']
    return label, score 


def perform_movement_sentiment(session, label, score):
    if label == "POS":
        # arms up for excitement/hooray 
        if score >= 0.95:
            perform_movement(session, 
                            frames = [{"time": 1200, "data":{"body.arms.right.upper.pitch":-2.59, "body.arms.left.upper.pitch":-2.59}},
                                    {"time": 2400, "data":{"body.arms.right.upper.pitch":0.0, "body.arms.left.upper.pitch":0.0}},
                                    ],
                                force = True)
            
        # yes node/tilting the head up
        else:
           perform_movement(session, 
                            frames = [{"time": 800, "data":{"body.head.pitch":-0.174}},
                                    {"time": 1600, "data":{"body.head.pitch": 0.0}},
                                    {"time": 2200, "data":{"body.head.pitch":-0.174}},
                                    {"time": 3000, "data":{"body.head.pitch":0.0}}],
                                force = True)
        # backward chest bent -> this needs to be changed and customised for backward 
        # if score < 0.9:
        #     perform_movement(session, 
        #                  frames = [{"time": 800, "data":{"body.legs.right.lower.pitch":0.0}},
        #                            {"time": 1600, "data":{"body.legs.right.lower.pitch":1.5}},
        #                            {"time": 8000, "data":{"body.legs.right.lower.pitch":0.0}}],
        #                     force = True)
       
    elif label == "NEG":
        # arms straight 
        if score >= 0.95:
            perform_movement(session, 
                         frames = [{"time": 700, "data":{"body.arms.right.lower.roll":0, "body.arms.left.lower.roll":0}},
                                   {"time": 1400, "data":{"body.arms.right.lower.roll": 6.50e-04, "body.arms.left.lower.roll": 6.50e-04}},
                                   {"time": 2100, "data":{"body.arms.right.lower.roll": -1.74, "body.arms.left.lower.roll": -1.74}},
                                   {"time": 5000, "data":{"body.arms.right.lower.roll":-1.74, "body.arms.left.lower.roll":-1.74}}, 
                                   {"time": 5700, "data":{"body.arms.right.lower.roll":-1, "body.arms.left.lower.roll":-1}}
                                   ],
                            force = True)
        # no node/tilting the head down  
        else:
            perform_movement(session, 
                         frames = [{"time": 800, "data":{"body.head.pitch":0.0}},
                                   {"time": 1600, "data":{"body.head.pitch": 0.174}},
                                   {"time": 2200, "data":{"body.head.pitch":0.0}},
                                   {"time": 3000, "data":{"body.head.pitch":0.174}},
                                   {"time": 3800, "data":{"body.head.pitch":0.0}}],
                            force = True)
        
        # foward chest bent  -> this needs to be changed 
        # if score < 0.9:
            # perform_movement(session, 
            #              frames = [{"time": 800, "data":{"body.legs.right.lower.pitch":0.0}},
            #                        {"time": 1600, "data":{"body.legs.right.lower.pitch":1.5}},
            #                        {"time": 8000, "data":{"body.legs.right.lower.pitch":0.0}}],
            #                 force = True)
        

        
        



    
@inlineCallbacks
def main(session, details):

    
    yield session.call("rom.optional.behavior.play", name = "BlocklyStand")
    #yield session.call("rie.vision.face.find")
    #yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    #yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward") # walking forward for introductory purpose
    #yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward")
    #session.call("rie.vision.face.track")
 
    
    

    # first three lines added for movement: standing and waiving at the beginning of the dialogue
    # second line: finding the face and tracking it (line4) 
    # yield session.call("rom.optional.behavior.play", name = "BlocklyStand")
    # # use this twice, we no longer need the walking part 
    # yield session.call("rie.vision.face.find")
    # sitting down for therapy 
    # yield session.call("rom.optional.behavior.play", name = "BlocklySitDown") 
    # yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    # # calling the TTS function for initiating the conversation, by passing the initial response 
    # session.call("rie.vision.face.track")


    label = None
    regular_sentence = "I am looking for the baseball cap."
    yield TTS_continuous(session, regular_sentence, label)
    trial_sentence = "I am looking for the baseball cap."
    yield TTS_continuous(session, trial_sentence, label)
    # calling the STT function for recognizing and processing the words from the user 
    #yield STT_continuous(session)

    

    session.leave() 

# realm should be changed based on the robot used 
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.6842b4f79827d41c07337bfd",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])