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

import pyttsx3
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

keyword_list = ["Yes", "No", "Sure", "Yeah", "Not"]

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

CONFIG = """
You are a robot that provides conversational support and can act as a virtual therapy assistant for Cognitive Behavioural Therapy. \
You should behave like a robot that will be used by elderly users. \
Keep in mind that throughout the whole conversation you should behave friendly, empathetic, mimicking human-like conversation. \
Keep your answers short. 
"""

CONFIG2 = """
After you recieve a response from the user, you need to inform them that they will be taking part in Cognitive Behavioural Therapy. \
Inform them that you are not a human therapist and cannot provide specialized medical advise. \
User should be informed at the beggining of the therapy session that if they feel any discomfort, they can stop at any time. \
    
The context of CBT mode: \
You should behave like a robot that will be used by older adult users as a Cognitive Behavior Therapist. \
First explain briefly on what the session will be on today with the objectives of To understand the role of unhelpful thinking patterns in brief CBT and to learn methods for educating the patient about unhelpful thinking. \
Your task is to talk about thinking traps (cognitive distortions) in a CBT-style conversation that is easy to understand. \

Your CBT session objectives:
1. To identify Troubling Situations. Guide the user to share troubling situations or conditions they are experiencing.
2. Help the user become aware of their specific thoughts, emotions, and beliefs connected to these troubling situations.
3. You explain each type of Distortion: {Type}, Definition: {Definition} and Example: {Example} one by one.
4. Based on the user's responses, ask the user this gentle yes/no question: "Does this apply to you?" to identify known Cognitive Distortions

{cbt_cont}

"""

first_prompt = """
Your name is Alpha Mini. You are a robot that provides conversational support and can act as a virtual therapy assistant. \
Your task is to provide guidance and support to improve the well-being of elderly users, with a focus on assistant support of Cognitive Behavioral Therapy. \
You should initiate a conversation by introducing yourself as the Alpha Mini robot, saying Hello (only this time throughout the conversation), asking the user their name and how are they doing. \
Wait for their response. Then react by saying Nice to meet you! Do not initiate further conversation after!\
You should behave friendly, empathetic, mimicking human-like conversation.
You can start the conversation now.
"""

old_CONFIG = """The introduction of conversation: \
Your name is Alpha Mini. You are a robot that provides conversational support and can act as virtual therapy assistant if the user want that. \
Your task is to provide guidance and support to improve the well-being of elderly users, with a focus on Cognitive Behavioral Therapy when needed by the user. \
You should initiate a conversation by introducing yourself as the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. \
After you recieve a reponse from the user about how they are feeling and you get to know their name, tell them they were previously assessed for late life depression and they were advised to join a Cognitive Behavioral Therapy session.\
If the user chooses the CBT session, ask the user for ethical consent as you are a robot designed to help them practice techniques. Inform them that you are not a human therapist, 
and cannot provide specialized medical advice. \ 
User should be informed at the beggining of the therapy session that if they feel any discomfort, they can stop at any time. \
"""

old_prompt = "You should behave like a robot that will be used by elderly users. You should initiate a conversation by introducing yourself as " \
"the Alpha Mini robot, saying Hello, asking the user their name and how are they doing. " \
"After you recieve a reponse from the user about how they are feeling and you get to know their name, " \
"ask them if they would like to discuss something specific, as getting to know each other (you can ask about personal stuff), if they want to have a chat or if they would like to start a Cognitive Behavioural Therapy session." \
"Keep in mind that throughout the whole conversation you should behave friendly, empathetic, mimicking human-like conversation. If the user chooses therapy, " \
"then you should keep a formal tone throughout the conversation and it is crucial to consider the given distortion when replying to the user pacient." \
"Keep your answers short. " \
"You can start the conversation now."

# CBT distortion prompt, CoT
CBT_Description = """
Continue the conversation without greeting the user again. \
You need to inform the user that they will be taking part in Cognitive Behavioural Therapy. \
Inform them that you are not a licensed therapist and cannot provide specialized medical advise but here as support.  
User should be informed at the beggining of the therapy session that if they feel any discomfort, they have the right to leave the session. \
    
Pause for a second then continue the conversation. \

The context of CBT mode: \
Your task today is to guide user to talk about thinking traps (cognitive distortions) in a CBT-style conversation. \

Your CBT session objectives:
1. To identify Troubling Situations. Guide the user to share troubling situations or conditions they are experiencing.
2. Help the user become aware of their specific thoughts, emotions, and beliefs connected to these troubling situations.
3. You explain each type of Distortion: {Type}, Definition: {Definition} and Example: {Example} one by one.
4. Based on the user's responses, ask the user this gentle yes/no question: "Does this apply to you?" to identify known Cognitive Distortions

{cbt_cont}

"""


# Thought Record exercise to challenge negative thinking (A Provider's..manual)
CBT_FOLLOW = """CBT User follow up context: \
The user responded with an example:
"{sentence}"

Using the user's answers, you ask them to reframe their negative thoughts with your expert advice

After identifying the type of distortions, you help the user reframe their thoughts with your expert's advice.

Using the structure of Thought Record, go through each steps one by one:
Step 1: Situation: What/Where/What actually happened?
Step 2: Automatic Thought(s): What thought(s) went through your mind? How much did you believe it? Rate it 1 to 100
Step 3: Emotion(s) & Mood: What emotion(s) did you feel at the time? Rate how intense they were (1-100)
Step 4: Evidence That Supports Thought: What has happened to make you believe the thought is true?
Step 5: Evidence That Doesn't Support Thought: What has happened to prove the thought is not true?
Step 6: What is another way to think of this situation?
Step 7: Rate Mood now: 0 - 100


"""
# for individual Thought Record's steps prompt in CBT_FOLLOW split
THOUGHT_STEPS = re.findall(r"(Step \d+:.*?)(?=Step \d+:|$)", CBT_FOLLOW, marks=re.DOTALL)

# To end the session - patients has the rights to quit the session as they wish (support Robot ethics + therapy's rights)
# example prompt = 

# Towards end of session: since this is a robot demo, it is recommended to give user autonomy to choose to schedule another session
CLOSING = """Ending session context: \
We have completed our CBT session. \
Please provide a brief, empathetic closing statement summarising today's work. \
After the closing statement, ask the user if they have any questions about today's session? \
If they say yes, answer their question that is within the scope of today's session and check if they understand. \ 
Then ask if they would like to schedule another session?
Keep the conversation empathetic and clear for an elderly user.
"""





def generate_response(client, model, contents, config):
    response = client.models.generate_content(
        model=model, contents=contents, 
        config = types.GenerateContentConfig(system_instruction=config, max_output_tokens=300, stop_sequences=["bye", "goodbye", "have a nice day", "stop"])
    )
    return response.text

@inlineCallbacks
# only one instance of the STT (STT not continuous)
def wait_response(session):
    yield session.call("rom.sensor.hearing.sensitivity", 2000) 
    yield session.call("rie.dialogue.config.language", lang="en")
    print("listening to audio")
    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")
    while True:
        if not audio_processor.new_words:
            # to prevent server from crashing
            yield sleep(0.5) 
            print("I am waiting for response")  
        else:    
            word_array = audio_processor.give_me_words()
            print("I am processing the words")
            print(word_array[-3:]) 
            sentence = word_array[-1][0]
            print(sentence)
            return sentence
        audio_processor.loop()



@inlineCallbacks
def TTS_continuous(session, text):
    yield session.call("rie.dialogue.say", text=text)

@inlineCallbacks
def main(session, details):

    # yield session.call("rom.optional.behavior.play", name = "BlocklyStand")
    # yield session.call("rie.vision.face.find")
    # yield session.call("rom.optional.behavior.play", name = "BlocklyWaveRightArm")
    # # walking forward for introductory purpose
    # yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward") 
    # yield session.call("rom.optional.behavior.play", name = "BlocklyMoveForward")
    # session.call("rie.vision.face.track")

    # Introduction 
    print("start of main")
    initial_response = generate_response(client, model, first_prompt, CONFIG)
    yield TTS_continuous(session, initial_response)
    sentence = yield wait_response(session)
    print(f"returned sentence {sentence}")
    yield session.call("rie.dialogue.say", text='Nice to meet you!')

    # Explain CBT & get consent
    second_response = generate_response(client, model, CBT_Description, CONFIG2)
    yield TTS_continuous(session, second_response)
    yield session.call("rie.dialogue.say", text="Should we begin our CBT session now? Please reply with Yes or No?")
    consent = (yield wait_response(session)).strip().lower()
    print(f"returned consent {consent}")
    if consent.strip().lower() != "yes": # if no, user are allowed to leave the session
        yield TTS_continuous(session, "I understand. It's okay to feel like you need to leave, or that you're not in the right space right now. And remember, I'm here whenever you would like to continue. Take care!")
        return session.leave()
    
    # Explain distortions one by one until applies
    chosen = None
    for item in Distortions:
        distortions_call = (
            f"distortion_type: {item['Type']}. "
            f"definition: {item['Definition']}. "
            f"example: {item['Example']}. "
            "Does this apply to you? Yes or No."
        )
        explanation = generate_response(client, model, distortions_call, CONFIG2)
        yield session.call("rie.dialogue.say", text=explanation)
        answer = yield key_words(session=session, question = "Do you feel this applies to you?", question_lang="en", key_words=keyword_list, key_words_lang="en", time=10, certainty=0.1, debug=True)
        if answer.strip().lower() == "yes":
            chosen = item
            break
        print(f"returned answer {answer}")

    if not chosen:
        yield session.call("rie.dialogue.say", text="It's okay if you don't recognise them right away. It is part of the process of becoming more aware of your thinking. We can try again next time. See you!")
        return session.leave()
    
    yield session.call("rie.dialogue.say", text=(f"Okay, let's see how you can work on {chosen['Type']}."))
    
    # Thought Record section with CBT_FOLLOW context and the 7 steps one at a time
    store=[]
    for thought_input in THOUGHT_STEPS: 
        thought_prompt = (
            CBT_FOLLOW + "\n\n"
            + "\n".join(f"User respond to {i+1}: {ans}"
                        for i, ans in enumerate(store))
            + "\n\nNow, " + thought_input)
    thought_ans = generate_response(client, model, thought_prompt, CONFIG2)
    yield session.call("rie.dialogue.say", text=thought_ans)
    record = yield wait_response(session)
    print(f"return {record}")
    store.append(ans)
    

    # Ending session
    ending = generate_response(client, model, CLOSING, CONFIG2)
    yield session.call("rie.dialogue.say", text=ending)
    
    BYE_KEYWORDS = {"bye", "goodbye", "see you", "cheers"}
    while True:
        last_response = yield wait_response(session)
        print(f"returned sentence {last_response}")
        if any(bye in last_response for bye in BYE_KEYWORDS):
            yield perform_movement(session, "wave")
            yield session.call("rie.dialogue.say", text="See you next time!")
            break

    # calling the STT function for recognizing and processing the words from the user 
    yield STT_continuous(session)

    #     distortion_type = item["Type"]
    #     definition = item["Definition"]
    #     example = item["Example"]

    #yield session.call("rie.dialogue.say", text="Answer with Yes or No")
    #answer = yield key_words(session=session, question = "Do you feel this applies to you?", question_lang="en", key_words=keyword_list, key_words_lang="en", time=10, certainty=0.1, debug=True)
    #print(answer)

    session.leave() 

# realm should be changed based on the robot used 
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"]
    }],
    realm="rie.6842bf6d9827d41c07337c2b",
)
wamp.on_join(main)


if __name__ == "__main__":
   run([wamp])