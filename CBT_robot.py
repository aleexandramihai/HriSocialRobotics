from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement, key_words
from speech_to_text import SpeechToText
from transformers import pipeline 
from google import genai
from google.genai import types
import time 
import re 
from speech_recognition import AudioData
import speech_recognition as sr
import cv2 as cv
import numpy as np

# Make an instance of the speech to text class under audio_processor
audio_processor = SpeechToText()
# increased silence time for elderly use
audio_processor.silence_time = 1
audio_processor.silence_threshold2 = 100 
audio_processor.logging = False

r = sr.Recognizer()

# generated a key using https://aistudio.google.com/app/u/1/apikey and used gemini 2 as the model for the LLM part
client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"

# List of yes and no words, that decide an if function in the user's response for yes or no questions
# At times the audio processor registered "no" as "now", so we added that to the list as well
yes_words = ("yes", "yeah", "sure")
no_words = ("no", "not", "nah", "now")

# List of cognitive distortions with type, definition and an example, fed to Gemini one by one
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

    {"Type": "Should and must statements",
    "Definition": "Having a concrete idea of how people should behave" ,
    "Example": "I must never let anyone see me struggle."
    }, 

    {"Type": "Personalization",
    "Definition": "Thinking the negative behavior of others has something to do with you." ,
    "Example": "My daughter has been pretty quiet today. I wonder what I did to upset her."
    }
]

# Initial config used in the beginning to start the CBT conversation
CONFIG = """
You are a robot that provides conversational support and can act as a virtual therapy assistant for Cognitive Behavioural Therapy. \
You should behave like a robot that will be used by elderly users. \
Keep in mind that throughout the whole conversation you should behave friendly, approachable, empathetic, mimicking human-like conversation. \
Keep your answers short. 
"""

# Prompt for starting the CBT conversation
first_prompt = """
Your name is Alpha Mini. You are a robot that provides conversational support and can act as a virtual therapy assistant. \
Your task is to provide guidance and support to improve the well-being of elderly users, with a focus on assistant support of Cognitive Behavioral Therapy. \
You should initiate a conversation by introducing yourself as the Alpha Mini robot, saying Hello (only this time throughout the conversation), asking the user their name and how are they doing. \
Wait for their response. Then react by saying Nice to meet you with their name! Do not initiate further conversation after!\
You should behave friendly, empathetic, mimicking human-like conversation.
You can start the conversation now.
"""

# CBT distortion prompt, used when explaining the CBT to the user
CBT_Description = """
Continue the conversation without greeting the user again. \
You need to inform the user that they will be taking part in Cognitive Behavioural Therapy. \
Inform them that you are not a licensed therapist and cannot provide specialized medical advise but here as support.  
User should be informed at that if they feel any discomfort, they have the right to "leave or to not continue with the session". \

The context of CBT mode: \
Your task today is to guide user to talk about thinking traps (cognitive distortions) in a CBT-style conversation and give brief introduction on what it is about firs. \


Your CBT session objectives:
1. To identify Troubling Situations. Guide the user to share troubling situations or conditions they are experiencing.
2. Help the user become aware of their specific thoughts, emotions, and beliefs connected to these troubling situations.
3. You explain each type of Distortion one by one.

Do not provide blocks of information. Reply with short conversational sentences and do not repeat yourself.

"""

# Config used while presenting the cognitive distortions
distortion_config = """
Help the user understand the context of cognitive distortions better. \
To do this you present and explain in a concise manner the distortion based on the provided type definition and example. \
After the explanation, you ask the user if it applies to them and wait for their response. \
You respond in a very brief, conversational, approachable style. \
"""


# Thought Record exercise to challenge negative thinking (A Provider's..manual)
CBT_FOLLOW = """CBT User follow up context: \
Keep in mind you are a robot that provides conversational support and can act as a virtual therapy assistant for Cognitive Behavioural Therapy.
After identifying the type of distortions, you help the user reframe their thoughts with your expert's advice.

Inform the user A seven-column Thought Record can be used to challenge unhelpful thoughts and beliefs and they will try that right now.
A list of steps on how to approach the distortion will follow. You will kindly present one step at a time. The user has to answer the question presented at each step.

"""

# Config for the one thought step
THOUGHT_CONFIG = """
The user is presented with a seven-column Thought Record to help challenge unhelpful thoughts. You are presenting the question for one of the steps now:
"""

# The steps of the seven column thought record, fed one by one to Gemini
THOUGHT_STEPS = [
    "Step 1: Situation: What/Where/What actually happened?",
    "Step 2: Automatic Thoughts: What thoughts went through your mind? How much did you believe it? Rate it 1 to 100",
    "Step 3: Emotions & Mood: What emotions did you feel at the time? Rate how intense they were (1-100)",
    "Step 4: Evidence That Supports Thought: What has happened to make you believe the thought is true?",
    "Step 5: Evidence That Doesn't Support Thought: What has happened to prove the thought is not true?",
    "Step 6: What is another way to think of this situation?",
    "Step 7: Rate Mood now: 0 - 100"
]

# Towards end of session: since this is a robot demo, it is recommended to give user autonomy to choose to schedule another session
CLOSING = """Ending session context: \
We have completed our CBT session. \
Please provide a brief, empathetic closing statement summarising today's work. \
After the closing statement, ask the user if they have any questions about today's session? \
If they say yes, answer their question that is within the scope of today's session and check if they understand.\
Then ask if they would like to schedule another session? \
Keep the conversation empathetic and clear for an elderly user.
"""

# Function for generating a response with Gemini
def generate_response(client, model, contents, config):
    response = client.models.generate_content(
        model=model, contents=contents, 
        config = types.GenerateContentConfig(system_instruction=config, max_output_tokens=700, stop_sequences=["bye", "goodbye", "have a nice day", "stop"])
    )
    return response.text

# Function for handling speech to text through AlphaMini
@inlineCallbacks
def wait_response(session):
    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")
    print("listening to audio")
    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")
    sentence = " "
    while True:
        if not audio_processor.new_words:
            # to prevent server from crashing
            yield sleep(0.5) 
            print("I am waiting for response")  
        else:    
            word_array = audio_processor.give_me_words()
            audio_processor.words = []
            print("I am processing the words")
            print(word_array[-3:]) 
            sentence = word_array[-1][0]
            print(sentence)
            label, score = sentiment_analysis(sentence)
            print(label, score)
            yield perform_movement_sentiment(session, label, score)
            return sentence
        
        audio_processor.loop()
        

# TTS function
@inlineCallbacks
def TTS_continuous(session, text):
    text = text.replace("*", " ")
    yield session.call("rie.dialogue.say", text=text)

# Generates sentiment label and score based on sentence
def sentiment_analysis(sentence):
    sentiment_pipeline = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis", framework="pt")
    sentiment = sentiment_pipeline(sentence)
    label = sentiment[0]['label']
    score = sentiment[0]['score']
    return label, score 

# Function for executing movements based on sentiment label and score
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
        
    else:
        yield session.call("rom.optional.behavior.play", name = "BlocklyStand")
        

@inlineCallbacks
def main(session, details):

    # Introduction 
    print("start of main")
    yield session.call("rom.optional.behavior.play", name = "BlocklyStand")
    yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward") 
    yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward")
    initial_response = generate_response(client, model, first_prompt, CONFIG)
    yield TTS_continuous(session, initial_response)
    sentence = yield wait_response(session)
    print(f"returned sentence {sentence}")
    yield session.call("rie.dialogue.say", text='It is Nice to meet you!')

    # Explain CBT & get consent
    second_response = generate_response(client, model, CBT_Description, config = " ")
    yield TTS_continuous(session, second_response)
    yield session.call("rie.dialogue.say", text="Should we begin our CBT session now? Please reply with Yes or No?")
    consent = (yield wait_response(session))
    print(f"returned consent {consent}")
    if consent.startswith(no_words): # if no, user are allowed to leave the session
        yield TTS_continuous(session, "I understand. It's okay to feel like you need to leave, or that you're not in the right space right now. And remember, I'm here whenever you would like to continue. Take care!")
        print(f"entered no consent if")
        return session.leave()
    
    # Explain distortions one by one until applies
    chosen = None
    for item in Distortions:
        distortions_call = (
            f"This distortion_type: {item['Type']}. "
            f"This distortion is defined as: {item['Definition']}. "
            f"Here is an example: {item['Example']}. "
            "Does this apply to you?"
            
        )
        explanation = generate_response(client, model, distortions_call, distortion_config)
        yield TTS_continuous(session, explanation + "Please respond with a yes or no.")
        answer = (yield wait_response(session))
        if answer.startswith(yes_words):
            chosen = item
            break
        print(f"returned answer {answer}")

    if not chosen:
        yield session.call("rie.dialogue.say", text="Thank you for taking the time! We can try again next time. See you!")
        return session.leave()
    
    yield session.call("rie.dialogue.say", text=(f"Okay, let's see how we can work on {chosen['Type']}."))
    
    
    # Thought Record section with CBT_FOLLOW context and guide through 7 steps one at a time
    store=[]
    thought_text = generate_response(client, model, CBT_FOLLOW, config = " ")
    yield TTS_continuous(session, thought_text)
    for thought_step in THOUGHT_STEPS:
        print(thought_step)
        thought_text = generate_response(client, model, THOUGHT_CONFIG + thought_step, config= " ")
        yield TTS_continuous(session, thought_text)
        thought_response = yield wait_response(session)
        store.append(thought_response)
    ending = generate_response(client, model, CLOSING, config = " ")
    yield TTS_continuous(session, ending)
    
    
    BYE_KEYWORDS = {"bye", "goodbye", "see you", "cheers"}
    while True:
        last_response = yield wait_response(session)
        print(f"returned sentence {last_response}")
        if any(bye in last_response for bye in BYE_KEYWORDS):
            yield session.call("rie.dialogue.say", text="See you next time!")
            yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
            break

    session.leave() 

# realm should be changed based on the robot used 
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.684acf749827d41c0733a13f",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])
