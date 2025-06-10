import gtts
import time 
from playsound import playsound 
from google import genai
from google.genai import types
import pyttsx3
import speech_recognition as sr
import re

client = genai.Client(api_key="AIzaSyBF7Pc46EszEBAAW_ecMhLYJT-dY_2qeB0")
model = "gemini-2.0-flash"

import pyttsx3

engine = pyttsx3.init()

first_prompt = """
Your name is Alpha Mini. You are a robot that provides conversational support and can act as a virtual therapy assistant. \
Your task is to provide guidance and support to improve the well-being of elderly users, with a focus on assistant support of Cognitive Behavioral Therapy. \
You should initiate a conversation by introducing yourself as the Alpha Mini robot, saying Hello (only this time throughout the conversation), asking the user their name and how are they doing. \
Wait for their response. Then react by saying Nice to meet you with their name! Do not initiate further conversation after!\
You should behave friendly, empathetic, mimicking human-like conversation.
You can start the conversation now.
"""

CONFIG = """
You are a robot that provides conversational support and can act as a virtual therapy assistant for Cognitive Behavioural Therapy. \
You should behave like a robot that will be used by elderly users. \
Keep in mind that throughout the whole conversation you should behave friendly, approachable, empathetic, mimicking human-like conversation. \
Keep your answers short. 
"""


CBT_Description = """
Continue the conversation without greeting the user again. \
You need to inform the user that they will be taking part in Cognitive Behavioural Therapy. \
Inform them that you are not a licensed therapist and cannot provide specialized medical advise but here as support.  
User should be informed at that if they feel any discomfort, they have the right to leave or to not continue with the session. \

The context of CBT mode: \
Your task today is to guide user to talk about thinking traps (cognitive distortions) in a CBT-style conversation and give brief introduction on what it is about firs. \


Your CBT session objectives:
1. To identify Troubling Situations. Guide the user to share troubling situations or conditions they are experiencing.
2. Help the user become aware of their specific thoughts, emotions, and beliefs connected to these troubling situations.
3. You explain each type of Distortion one by one.

Do not provide blocks of information. Reply with short conversational sentences and do not repeat yourself.

"""
Distortions = [
    {"Type": "Personalization",
    "Definition": "Thinking the negative behavior of others has something to do with you." ,
    "Example": "My daughter has been pretty quiet today. I wonder what I did to upset her."
    },
    
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
    }
]


distortion_config = """
Help the user understand the context of cognitive distortions better. \
To do this you present and explain in a concise manner the distortion based on the provided type definition and example. \
After the explanation, you ask the user if it applies to them and wait for their response. \
You respond in a very brief, conversational, approachable style. \
"""

CBT_FOLLOW = """CBT User follow up context: \
Keep in mind you are a robot that provides conversational support and can act as a virtual therapy assistant for Cognitive Behavioural Therapy.
After identifying the type of distortions, you help the user reframe their thoughts with your expert's advice.

Inform the user A seven-column Thought Record can be used to challenge unhelpful thoughts and beliefs and they will try that right now.
A list of steps on how to approach the distortion will follow. You will kindly present one step at a time. The user has to answer the question presented at each step.

"""

THOUGHT_CONFIG = """
The user is presented with a seven-column Thought Record to help challenge unhelpful thoughts. You are presenting the question for one of the steps now:
"""

THOUGHT_STEPS = [
    "Step 1: Situation: What/Where/What actually happened?",
    "Step 2: Automatic Thought(s): What thought(s) went through your mind? How much did you believe it? Rate it 1 to 100",
    "Step 3: Emotion(s) & Mood: What emotion(s) did you feel at the time? Rate how intense they were (1-100)",
    "Step 4: Evidence That Supports Thought: What has happened to make you believe the thought is true?",
    "Step 5: Evidence That Doesn't Support Thought: What has happened to prove the thought is not true?",
    "Step 6: What is another way to think of this situation?",
    "Step 7: Rate Mood now: 0 - 100"
]

CLOSING = """Ending session context: \
We have completed our CBT session. \
Please provide a brief, empathetic closing statement summarising today's work. \
After the closing statement, ask the user if they have any questions about today's session? \
If they say yes, answer their question that is within the scope of today's session and check if they understand.\
Then ask if they would like to schedule another session? \
Keep the conversation empathetic and clear for an elderly user.
"""

r = sr.Recognizer()

def generate_response(client, model, contents, config):
    response = client.models.generate_content(
        model=model, contents=contents, 
        config = types.GenerateContentConfig(system_instruction=config, max_output_tokens=300, stop_sequences=["bye", "goodbye", "have a nice day", "stop"])
    )
    return response.text

initial_response = generate_response(client, model, first_prompt, CONFIG)



def SpeakText(response, rate):
    engine = pyttsx3.init()
    engine.setProperty('rate', rate)
    engine.say(response)
    engine.runAndWait()

def adapt_rate(rate, user_response, duration):
    word_count = len(user_response.split())
    user_speaking_speed = (word_count / duration) * 60 
    if abs(rate - int(user_speaking_speed)) >=10 :
        if abs(int(user_speaking_speed)) <=170:
            rate = 170
        else:
            rate = int(user_speaking_speed)
    return rate


# inspired from https://www.geeksforgeeks.org/python-convert-speech-to-text-and-text-to-speech/

def main():
   store = []
   rate = 200
   SpeakText(initial_response, rate)
   while(True):
        try: 
            with sr.Microphone() as source2:
                
                # wait for a second to let the recognizer
                # adjust the energy threshold based on
                # the surrounding noise level 
                r.adjust_for_ambient_noise(source2, duration=0.2)
                print("I am listening")

                #listens for the user's input 
                start_time = time.time()
                audio2 = r.listen(source2)
                end_time = time.time()

                duration = end_time - start_time
                print("duration is:", duration)

                
                # Using google to recognize audio
                user_response = r.recognize_google(audio2)
                user_response = user_response.strip().lower()
                print("This is user response:", user_response)

        
        except sr.RequestError as e:
            print("Could not request results;", e)
            
        except sr.UnknownValueError:
            print("Unknown error occurred")
        
        SpeakText("Nice to meet you! Should we begin our CBT session now? Please reply with Yes or No.", adapt_rate(rate, user_response, duration))
        while(True):
            try: 
                with sr.Microphone() as source2:
                    
                    # wait for a second to let the recognizer
                    # adjust the energy threshold based on
                    # the surrounding noise level 
                    r.adjust_for_ambient_noise(source2, duration=0.2)
                    print("I am listening")

                    #listens for the user's input 
                    start_time = time.time()
                    audio2 = r.listen(source2)
                    end_time = time.time()

                    duration = end_time - start_time
                    print("duration is:", duration)

                    
                    # Using google to recognize audio
                    user_response = r.recognize_google(audio2)
                    user_response = user_response.strip().lower()
                    print("This is user response:", user_response)

                    if "yes" in user_response:
                        for item in Distortions:
                            distortions_call = (
                                f"This distortion_type: {item['Type']}. "
                                f"This distortion is defined as: {item['Definition']}. "
                                f"Here is an example: {item['Example']}. "
                                "Does this apply to you?"
                                )
                            explanation = generate_response(client, model, distortions_call, distortion_config)
                            explanation = re.sub("[^A-Za-z0-9]"," ", explanation)
                            SpeakText(explanation, adapt_rate(rate, user_response, duration))
                            SpeakText("Please respond with a yes or no.", adapt_rate(rate, user_response, duration))
                            while(True):
                                try: 
                                    with sr.Microphone() as source2:
                                        
                                        # wait for a second to let the recognizer
                                        # adjust the energy threshold based on
                                        # the surrounding noise level 
                                        r.adjust_for_ambient_noise(source2, duration=0.2)
                                        print("I am listening")

                                        #listens for the user's input 
                                        start_time = time.time()
                                        audio2 = r.listen(source2)
                                        end_time = time.time()

                                        duration = end_time - start_time
                                        print("duration is:", duration)

                                        
                                        # Using google to recognize audio
                                        user_response = r.recognize_google(audio2)
                                        user_response = user_response.strip().lower()
                                        print("This is user response:", user_response)

        
                                except sr.RequestError as e:
                                    print("Could not request results;", e)
                                    
                                except sr.UnknownValueError:
                                    print("Unknown error occurred")
                                if "yes" in user_response:
                                    for thought_step in THOUGHT_STEPS:
                                         print(thought_step)
                                         thought_text = generate_response(client, model, THOUGHT_CONFIG + thought_step, config= None)
                                         SpeakText(thought_text, adapt_rate(rate, user_response, duration))
                                         while(True):
                                            try: 
                                                with sr.Microphone() as source2:
                                                    
                                                    # wait for a second to let the recognizer
                                                    # adjust the energy threshold based on
                                                    # the surrounding noise level 
                                                    r.adjust_for_ambient_noise(source2, duration=0.2)
                                                    print("I am listening")

                                                    #listens for the user's input 
                                                    start_time = time.time()
                                                    audio2 = r.listen(source2)
                                                    end_time = time.time()

                                                    duration = end_time - start_time
                                                    print("duration is:", duration)

                                                    
                                                    # Using google to recognize audio
                                                    user_response = r.recognize_google(audio2)
                                                    user_response = user_response.strip().lower()
                                                    print("This is user response:", user_response)

                                                    break

                                            
                                            except sr.RequestError as e:
                                                print("Could not request results;", e)
                                                
                                            except sr.UnknownValueError:
                                                print("Unknown error occurred")
                                         
                                
                    else: 
                        SpeakText("I understand. It's okay to feel like you need to leave, or that you're not in the right space " \
                        "right now. And remember, I'm here whenever you would like to continue. Take care!",adapt_rate(rate, user_response, duration))


            
            except sr.RequestError as e:
                print("Could not request results;", e)
                
            except sr.UnknownValueError:
                print("Unknown error occurred")

    


if __name__ == "__main__":
    main()