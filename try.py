print("code runs hopefully")


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
    "Definition": "Placing all one’s attention on, or seeing only, the negatives of a situation",
    "Example": "My daughter would never do anything I disapproved of"
    },

    {"Type": "Overgeneralization",
    "Definition": "Making an overall negative conclusion beyond the current situation.",
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

for item in Distortions:
    distortion_type = item["Type"]
    definition = item["Definition"]
    example = item["Example"]
    
    print(f"Type: {distortion_type}")
    print(f"Definition: {definition}")
    print(f"Example: {example}")
