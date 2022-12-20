import tkinter
from tkinter import *
import nltk
nltk.download('punkt')
nltk.download('wordnet')
from nltk.stem import WordNetLemmatizer
lemmatizer = WordNetLemmatizer()
import json
import pickle
import numpy as np
import random
from keras.models import Sequential
from keras.models import load_model
from keras.layers import Dense, Activation, Dropout
from keras.optimizers import SGD

words = []
classes = []
documents = []
ignore = ['?', '!']
intents_file = open('intents.json').read()
intents = json.loads(intents_file)

# pre-process natural langauge data
for i in intents['intents']:
    for p in i['patterns']:
        # tokenize the natural language
        word = nltk.word_tokenize(p)
        words.extend(word)
        documents.append((word, i['tag']))
        # add the different tags to classes,
        # while making sure it's only done once
        if i['tag'] not in classes:
            classes.append(i['tag'])

# lemmatize all the pre-processed data
words = [lemmatizer.lemmatize(w.lower()) for w in words if w not in ignore]
# sort our words and classes in a list
words = sorted(list(set(words)))
classes = sorted(list(set(classes)))

print (len(documents), "documents")

print (len(classes), 'classes', classes)

print (len(words), "unique lemmatized words", words)

pickle.dump(words, open('words.pkl', 'wb'))
pickle.dump(classes, open('classes.pkl', 'wb'))

# init training data
training = []
output_empty = [0] * len(classes)
for doc in documents:
    # init bag of words
    bag = []
    
    # list of tokenized words to use for the pattern
    pattern_words = doc[0]
    # now we lemmatize each word, essentially creating the base word in an attempt to represent related words
    pattern_words = [lemmatizer.lemmatize(word.lower()) for word in pattern_words]
    # create an array with 1 in relation to our bag of words, if the word match is found in the current pattern
    for w in words:
        bag.append(1) if w in pattern_words else bag.append(0)
        
    # output is 0 for each tag and 1 for current tag
    output_row = list(output_empty)
    output_row[classes.index(doc[1])] = 1
    
    training.append([bag, output_row])
# shuffle the features and turn into a numpy array
random.shuffle(training)
training = np.array(training)
# create train and test lists. x is patterns and y is intents
train_x = list(training[:, 0])
train_y = list(training[:, 1])
print("Training data successfully created")

# create a model with 3 layers, first layer has 128 neurons, second 64, third has number of neurons
# equal to number of intents to predict output intent with softmax
model = Sequential()
model.add(Dense(128, input_shape=(len(train_x[0]), ), activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.5))
model.add(Dense(len(train_y[0]), activation='softmax'))

# compile the model, stohastic gradient descent with nesterov accelerated gradient gives good results
sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])

# fit and save the model
hist = model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1)
model.save('winechatbotmodel.h5', hist)
print("model created")

model = load_model('winechatbotmodel.h5')
words = pickle.load(open('words.pkl', 'rb'))
classes = pickle.load(open('classes.pkl', 'rb'))

def clean_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

# return bag of words array, 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=True):
    #tokenize our pattern
    sentence_words = clean_sentence(sentence)
    # our bag of words - matrix of N words, vocabulary matrix
    bag = [0] * len(words)
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s:
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" %w)
    return(np.array(bag))

def predict_class(sentence, model):
    #filter out predictions
    p = bow(sentence, words, show_details=True)
    res = model.predict(np.array([p]))[0]
    # threshold which is the lowest value a prediction can be to considered
    # an eligible prediction
    PREDICT_THRESHOLD = 0.25
    result = [[i,r] for i,r in enumerate(res) if r > PREDICT_THRESHOLD]
    #sort it by the strength of possibility, most probable at index 0
    result.sort(key=lambda x: x[1], reverse = True)
    r_list = []
    for r in result:
        # append to our return list in regard to what has the highest likelihood
        r_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return r_list

def fetch_response(ints, intents_json):
    # fetch the relevant intent from our predict class function
    tag = ints[0]['intent']
    # get the list of our intents from our json file
    intents_list = intents_json['intents']
    # iterate through the tags until we find the matching tag
    for i in intents_list:
        if(i['tag'] == tag):
            # choose a random response from the responses
            result = random.choice(i['responses'])
            break
    return result

def chatbot_response(response):
    # predict the intent of our user
    ints = predict_class(response, model)
    # use the predicted intent to fetch relevant response
    response = fetch_response(ints, intents)
    return response

#Creating GUI with tkinter
import tkinter
from tkinter import *


def send():
    msg = EntryBox.get("1.0",'end-1c').strip()
    EntryBox.delete("0.0",END)

    if msg != '':
        ChatLog.config(state=NORMAL)
        ChatLog.insert(END, "You: " + msg + '\n\n')
        ChatLog.config(foreground="#442265", font=("Verdana", 12 ))

        res = chatbot_response(msg)
        ChatLog.insert(END, "Bot: " + res + '\n\n')

        ChatLog.config(state=DISABLED)
        ChatLog.yview(END)


base = Tk()
base.title("Wine chatbot")
base.geometry("400x500")
base.resizable(width=FALSE, height=FALSE)

#Create Chat window
ChatLog = Text(base, bd=0, bg="white", height="8", width="50", font="Arial",)

ChatLog.config(state=DISABLED)

#Bind scrollbar to Chat window
scrollbar = Scrollbar(base, command=ChatLog.yview, cursor="heart")
ChatLog['yscrollcommand'] = scrollbar.set

#Create Button to send message
SendButton = Button(base, font=("Verdana",12,'bold'), text="Send", width="12", height=5,
                    bd=0, bg="#32de97", activebackground="#3c9d9b",fg='#ffffff',
                    command= send )

#Create the box to enter message
EntryBox = Text(base, bd=0, bg="white",width="29", height="5", font="Arial")
#EntryBox.bind("<Return>", send)


#Place all components on the screen
scrollbar.place(x=376,y=6, height=386)
ChatLog.place(x=6,y=6, height=386, width=370)
EntryBox.place(x=128, y=401, height=90, width=265)
SendButton.place(x=6, y=401, height=90)

base.mainloop()