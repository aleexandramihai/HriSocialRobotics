# Human Robot Interaction for Social Robots - Final Project


Our project contains three main parts that were described in depth in the report. The CBT therapy module is implemented in all three files, while the Sentiment Analysis module is only implemented in the CBT_robot.py and CBT_audio_laptop.py, which are the files that have to be run in order to see the functionality on the robot. The speaking pace adaptation module was implemented in the speaking_pace_adaptation.py. Note that for this file you do not need to connect to the robot, it only runs on a laptop. 

The CBT_audio_laptop.py was created because we noticed some problems in the Speech-To-Text module when running the CBT_robot.py, as it would not register our responses, displaying "I am listening" even though we already said the prompt. We will describe the implementation in more detail in a following section. 

## CBT_robot.py 

After we implemented the libraries that we need, we created an instance of the speech to text class and we named it audio_processor. We then set the attributes to the values suggested in the Alpha Mini Robot manual. 

We generated a key and defined a client and a model, that we later used in the generate_response function, that we use to generate responses with Gemini, where we pass a contents parameter, that should contain the user response, and a config prompt. There are multiple config prompts designed and passed in the code, and a more in depth explanation of those can be found in the report. 

We define two list of keywords, for yes and for no words, that we will later use in the process of capturing responses from the user. 

The sentiment_analysis function takes as argument the sentence (which should be the user's response), on which we apply a pipeline that is based on the pre-trained BERTweet model for the sentiment analysis task. Then, we take the label and the score and we return it. 

The perform_movement_sentiment function takes as argument the label and the score (besides the session, that is needed for the connection to the robot that makes the following movements possible). We then check whether the label is positive or negative. If it is positive, and it has a score greater or equal to 0.95, the robot performs an arms up movement. If the score is lower, then it tilts the head up. For the negative laptop, we apply the same mechanism, and the first movement is represented by a straight arms movement, while the other movement is represented by tilting the head down. The movements were implemented using the function perform_movement, that takes as argument the session, the frames, which we mainly took from the appendix of the Alpha Mini Robot manual, including the times and the values of the function responsible for the movements. Fo this part, we took more values from the range given in the manual, and we kept the ones that yielded the best results (the most natural behaviour). If the passed sentiment is neutral, then the robot performs the BlocklyStand movement that is also performed at the beggining of the conversation. 

We created the wait_response function that handles speech to text through the Alpha Mini robot, that is mainly inspired from the SpeechToText function presented in the manual. The main difference is that we return the captured sentence instead of using the TextToSpeech function here that "says" the generated response based on the given sentence. We did this because, at certain times thoughout the conversation, we have to check whether the sentence contains specific keywords, in order to generate the next response. 

At the beginning of the conversation, the robot stands straight, waives their right arm and then makes two steps forward. For implementing these movements, we called the respective function as they mention in the manual's appendix. The robot then generates the initial response, where they greet the user and "says it" thorugh the TTS function. After the user responds, the robot says "it is nice to meet you!"

The robot describes the CBT session, by generating a response, using the generate_response function, where we pass a specific prompt for this, which is the CBT_description, and an empty config prompt, since we do not need to rely on any other core informaion for this. The robot asks the user if they should begin the session and instructs them to answer with a yes or no. Then, we capture the user's response using the wait_response function, and we check whether it contains words from the yes or no keywords lists defined earlier. If they answer with "no" or other variations, the robot responds with a pre-set message about the fact that it understands the user and greets it goodbye. After this, the session ends. 

If the user answered with a yes, we go through all the distortions described in the Distortion prompt, and we create a distortion_call from each one of them, where we define the type, the definition and an example. We use this to create an explanation that is fed to the LLM together with the distortion_config prompt, and said out loud to the user. The robot also asks if this applies to them. If the robot went through all distortions, and none of those were chosen (the user replied with no to each one of them), the robot says that they can talk about it next time and the session ends. 


If there is a positive answer we select the distortion as "chosen" and we break as we already identified the problem. Then, we start the thought record exercise by going through all the 7 steps presented in the prompt THOUGHT_STEPS, where we generate a response based on the step, we wait for the user to answer and the robot then goes to the next step. After they went through all the steps, the robot ends the conversation with a closing statement. If there are any goodbye words from the bye_lists in the user's response, the robot says "See you next time!" and the session ends. 




## Speaking_pace_adaptation.py

For this file, we kept all the prompts from the previous code file. We used pyttsx3 lybrary, for the text-to-speech module and the speech recognition library for the speech to text file. 

The generate_response function is the same as in the previous file. 

We created an instance of the recognizer class that we will later use in capturing the user response. 
Then, we created the SpeakText function, that takes as arguments the response (generated by Gemini) and the rate. We inspired from the python documentation https://pyttsx3.readthedocs.io/en/latest/engine.html in the creation of this function. 

The adapt_rate function receives as arguments the rate that should be used when "speaking" the user_response captured, and the duration that we get later from the main code, where we use a start time and an end time before and after we listen to the user. The duration comes from their difference. We then take the number of words by taking the length of the user response after we split it in words, and calculate the user speed by dividing the word count by duration and we multiply it by 60 in order to receive the answer in seconds. Then we check to see whther the difference between the rate (which is set at the default 200 at the beginning) and the user speaking rate is bigger than 10. If the user's speaking speed is less than or equal to 170, then we set the rate to 170, otherwise we keep the user's speaking rate. 

In the main code part, we first "say" the first generated response where we are greeting the user, and then we are listening to the user. The implementation of the while loop is inspired from https://www.geeksforgeeks.org/python-convert-speech-to-text-and-text-to-speech/. The rest of the conversation follows as the one presented in the previous file, however, using the SpeakText for the Text to Speech functionality and the while loop with the speech recognizer for the Speech to Text functionality. 


## CBT_audio_laptop.py 

This file behaves similarly to the first CBT_robot file. However, when we tried testing the latter's functionality, we discovered that the speech to text (wait_response) function does not function as expected, because it did not record all the words that we said. Hence, in order to test the other functionalities, we created a new file, where the wait_response function, that is responsible for capturing the user's response, has been replaced with an input_response function. In its implementation, we used the while loop designed in the previous file, and adapt it to this file. This means that the laptop handles the process of capturing the spoken reply, instead of the robot. 
