# Human-Robot Interaction for Social Robotics 
Coding assignemnt - group 6 

Before running the code, one should change the realm in the Component class, according to the robot they will be using. 
For the implementation of this assignment, we relied on the Manual Advanced Programming provided through the course.

We first created an instance of the SpeechToText class, audio_processor, set the silence time responsible for stopping the recording to 3 (to account for elderly use) and set the silence threshold2 to 100, meaning that any sound recorded below this value is considered silence. 

For creating the API key, we used information from this website https://aistudio.google.com/app/u/1/apikey  and for generating the responses we used the gemini 2.0 flash model for the LLM integration part. 

The creation of the CONFIG and the new_prompt prompts was inspired from Esteban-Lozano et al. (2024). 

We then define a generate_response function (that we took from https://ai.google.dev/api/generate-content), where we generate the content by passing the CONFIG prompt as the system instructions. This way, the LLM considers this prompt each time it generates a new response. Moreover, we set the max_output_token to 100, meaning that the maximum number of words a generated response should have would be 100, suhc that the conversation is kept short and we also added some stop_sentences, namely "bye", "goodbye", "have a nice day" and "stop". 

We then create an initial response, by passing the new_prompt as the contents and the CONFIG. This will be later used in the main loop for initiating the conversation. 

We define the TTS_continuous function as presented in the manual, and we use "say_animated" such that the robot also performs movement while speaking. 

The STT_cotinuous function is also defined as presented in the manual. At first, the robot "hears" what the elderly person says, and then it processes it. The hearing sensitivity is set to 2000, to account for elderly use and the language is set to English. 
The robot starts listening and we turn the microphone off in order for it not to start a conversation with itself. (In order fot his to work properly, we think that we should have used the yield function, however, this occured to us after our last robotics lab, and we could not have that tested out. Hence, we decided not to change the code to prevent any possible occuring errors.) The model then selects what the user said last and generated a response based on this sentence. We then call the TTS_continuous function to generate speach from the generated content, and turn the microphone on. 

In the main fucntion, the robots stands up and waives its right hand at the start of the dialogue, which then starts, by calling the TTS_continuous function and passing the initial_response as the content. The user is expected to respond back to the robot, and their answer is then transformed within the STT_continuous function, to which the robot answers back. 
