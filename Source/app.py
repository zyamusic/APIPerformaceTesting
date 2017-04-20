import os
import re
import csv
import glob
import json
import time
import shutil
import codecs
import tweepy
import urllib
import itertools as itt
from flask import request
import xml.etree.ElementTree as ET
from werkzeug import secure_filename
from flask import Flask,render_template, redirect, url_for


keyFile = open('keys.txt', 'r')
consumer_key = keyFile.readline().rstrip()
consumer_secret = keyFile.readline().rstrip()
access_key = keyFile.readline().rstrip()
access_secret = keyFile.readline().rstrip()

###########TWITTER
# consumer_key = "v7wZkFPdDRHbOonYThE16iuUT"
# consumer_secret = "73Xw5KSHpQwf7vQuopBnKuBnj51KNjdJ8e5WydqlSWGJO3bzIH"
# access_key = "836659939468685312-L4vLa4e15ql3LG1Dm34vR0TlwxYeoTP"
#access_secret = "y4lwfiwEKIWs2XsUwOTqR810c7iLVrDGDJO2pgCxwSki1"
###########TWITTER

app = Flask(__name__)
JMETER = '/usr/local/bin/jmeter'
workingDir = os.getcwd()
CONFIG = workingDir + '/../JMeterConfig/config.jmx'
outputDir = 'static/'
OUTPUT = outputDir + 'Output/'
SONGS = os.getcwd() + "/../../DittyAudioContent/content/audio/songs"
allParams = {
    'targetServer':'localhost','targetPort':'8080', 'cwd':'.','out_cfg':'static/Output/',
    'shiftBufferBy':6,'num_Dittys':200, 'writeOnBgThread':0,
    'bypassOGGEncoding':0, 'useSubProcess':0
}

shiftOptions = ['4', '5','6','7','8']
threadedOptions = ['0','1']
bypassOptions = ['0','1']
SubprocOptions = ['0','1']

jMeterArgs = {}

# Homepage
@app.route('/')
@app.route('/index')
def index():
    # update test params
    global allParams
    allParams = GetNewJMX()

    # display all summary files
    summaries = {}
    for outFile in glob.iglob('static/Output/**/*.html'):
        print outFile
        summaries[outFile] = '/' + outFile
    return render_template('index.html', summaries=summaries, allParams=allParams)

# Testing area
@app.route('/executeTest', methods=['GET','POST'])
def executeTest():
    global OUTPUT
    global allParams
    if request.method == 'GET':
        allParams = GetNewJMX()
        summaries = {}
        for outFile in glob.iglob('static/Output/**/*.html'):
            print outFile
            summaries[outFile] = '/' + outFile
        return render_template('index.html', summaries=summaries, allParams=allParams)

    else:
        # Get test params
        for arg,val in allParams.iteritems():
            print arg
            jMeterArgs[arg] = request.form[arg]

        # Check if running permutations
        runVars = request.form.get('RunVariations')
        if runVars:
            runVariations()
        else:
            # Update configs values
            print 'making conifg'
            tree = ET.parse(CONFIG)
            root = tree.getroot()
            for neighbor in root.iter('elementProp'):
                if 'Argument' == neighbor.get('elementType'):
                    for child in neighbor.iter('stringProp'):
                        if child.attrib.get('name') == 'Argument.value':
                            currentArg = neighbor.attrib.get('name')
                            child.text = jMeterArgs[currentArg]
                            print neighbor.attrib.get('name') + ' = ' + child.text

            tree.write(CONFIG)

            # prepare outut strings
            timestr = time.strftime("%H%M%S")
            OUTPUT = 'static/Output/' + timestr
            for arg, val in allParams.iteritems():
                OUTPUT += '_' + arg[0] + jMeterArgs[arg]

            OUTPUT_HTML = OUTPUT + '_HTML'
            OUTPUTFile = OUTPUT + '.csv'

            # Run jmeter command
            print JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML

            os.system(JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML)

        return redirect(url_for('index'))

# Configure the dataset
@app.route('/configData', methods=['GET','POST'])
def configData():
    # Get mic ids for form'
    allMics = getAllMicIDs()

    if request.method == 'GET':
        summaries = {}
        for outFile in glob.iglob('static/Output/**/*.html'):
            print outFile
            summaries[outFile] = '/' + outFile
        return render_template('configData.html', summaries=summaries, allMics=allMics)

    else:
        selectedMicID = request.form['MicID']
        tweetUser = request.form['TwitterUser']
        tweetCount = request.form['TweetCount']

        # Prepare dataset
        alltweets = getAllTweets(tweetUser,tweetCount)
        allSongs = getAllSongs(selectedMicID)
        dataPairs = []
        for permutation in itt.product(alltweets,allSongs):
            dataPairs.append(permutation)

        # Write dataset
        writeDataFile(dataPairs)

        return render_template('configData.html',allMics=allMics,alltweets=alltweets)

# Upload a new configuration
@app.route('/upload_jmx', methods=['GET','POST'])
def upload_jmx():
    global allParams
    print 'UPLOADING'

    if request.method == 'GET':
        allParams = GetNewJMX()
        return render_template('upload_jmx.html')

    else:
        # Save old versions and update for new config
        # Put in static folder to serve them over http
        timestr = time.strftime("%H%M%S")
        f = request.files['file']
        f.save(secure_filename(f.filename))

        shutil.copy(os.getcwd() + '/../JMeterConfig/config.jmx',os.getcwd() + '/../JMeterConfig/' + timestr + 'config.jmx')
        shutil.copy(os.getcwd() + '/static/config.jmx',os.getcwd() + '/static/' + timestr + 'config.jmx')
        shutil.copy(f.filename, os.getcwd() + '/static/config.jmx')
        shutil.copy(f.filename, os.getcwd() + '/../JMeterConfig/config.jmx')
        allParams = GetNewJMX()

        return render_template('upload_jmx.html')

# Get all songs based on mic id
def getAllSongs(micID):
    songs = []
    for item in [d for d in os.listdir(SONGS) if os.path.isdir(os.path.join(SONGS, d))]:
        if not item.startswith('.'):
            jsonFile = SONGS + '/' + item + '/' + item + '.json'
            if os.path.exists(jsonFile):
                with codecs.open(jsonFile,'r',encoding='utf-8') as file:
                    if any(micID in line for line in file):
                        songs.append(item.encode('utf-8'))
    return songs

# Get all mic ids in the repo
def getAllMicIDs():
    mics = set()
    for item in [d for d in os.listdir(SONGS) if os.path.isdir(os.path.join(SONGS, d))]:
        if not item.startswith('.'):
            jsonFile = SONGS + '/' + item + '/' + item + '.json'
            if os.path.exists(jsonFile):
                with open(jsonFile) as jFile:
                    for line in jFile:
                        if 'micID' in line:
                            mic = line.split(':')[1].strip().replace('\"','').replace(',','')
                            mics.add(mic)
    return mics

# Get a specified number of tweets from a twitter user
def getAllTweets(screen_name, tweetCount):
    tweetCount = int(tweetCount)
    tweetText = []
    #Twitter only allows access to a users most recent 3240 tweets with this method

    #authorize twitter, initialize tweepy
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    api = tweepy.API(auth)

    #initialize a list to hold all the tweepy Tweets
    alltweets = []

    #make initial request for most recent tweets (200 is the maximum allowed count)
    if tweetCount > 200:
        new_tweets = api.user_timeline(screen_name = screen_name,count=200)
        #save most recent tweets
        alltweets.extend(new_tweets)
        oldest = alltweets[-1].id - 1

        #keep grabbing tweets until there are no tweets left to grab
        while len(new_tweets) > 0 and len(alltweets) < tweetCount:

            #all subsiquent requests use the max_id param to prevent duplicates
            new_tweets = api.user_timeline(screen_name = screen_name,count=200,max_id=oldest)

            #save most recent tweets
            alltweets.extend(new_tweets)

            #update the id of the oldest tweet less one
            oldest = alltweets[-1].id - 1

    else:
        new_tweets = api.user_timeline(screen_name = screen_name,count=tweetCount)
        alltweets.extend(new_tweets)

    for tweet in alltweets:
        if len(tweetText) <= tweetCount:
            tweetText.append(tweet.text)
    return tweetText

# Writes the dataset of (text,song)
def writeDataFile(pairs):
    csv_data_file_name = "static/CSV_Data_File.csv"

    with open( csv_data_file_name, 'w' ) as csvfile:
        for p in pairs:
            t,s=p
            text = urllib.quote_plus( t.encode('utf-8') )
            song = s.encode('utf-8')
            text = re.sub(r"http\S+", "", text) # Remove http links
            if isNotBlank(text) and isNotBlank(song):
                csvfile.write( text + "," + song + "\n" )

    shutil.copy(csv_data_file_name, os.getcwd() + '/CSV_Data_File.csv')

# Runs all permutations of perfrmance tests
def runVariations ():
    allCombos = itt.product(shiftOptions, threadedOptions, bypassOptions, SubprocOptions)

    for shift,thread,bypass,subproc in allCombos:
        jMeterArgs['shiftBufferBy'] = shift
        jMeterArgs['writeOnBgThread'] = thread
        jMeterArgs['bypassOGGEncoding'] = bypass
        jMeterArgs['useSubProcess'] = subproc

        if subproc == '0' and bypass == '0':
            print 'Unneccessary run'
        else:
            tree = ET.parse(CONFIG)
            root = tree.getroot()
            for neighbor in root.iter('elementProp'):
                if 'Argument' == neighbor.get('elementType'):
                    for child in neighbor.iter('stringProp'):
                        if child.attrib.get('name') == 'Argument.value':
                            currentArg = neighbor.attrib.get('name')
                            child.text = jMeterArgs[currentArg]
                            print neighbor.attrib.get('name') + ' = ' + child.text

            tree.write(CONFIG)

            timestr = time.strftime("%Y%m%d-%H%M%S")
            OUTPUT = 'static/Output/' + timestr + '_' + jMeterArgs['targetServer'] + '_' + jMeterArgs['num_Dittys'] + '_' + jMeterArgs['shiftBufferBy'] + '_' + jMeterArgs['writeOnBgThread'] + '_' + jMeterArgs['bypassOGGEncoding'] + '_' + jMeterArgs['useSubProcess']

            OUTPUT_HTML = OUTPUT + '_HTML'
            OUTPUTFile = OUTPUT + '.csv'

            print JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML

            os.system(JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML)
        print 'starting next permutation'

# Updates the dictionary that holds the test parameters
def GetNewJMX():
    tree = ET.parse(CONFIG)
    root = tree.getroot()
    allParams = {}
    for neighbor in root.iter('elementProp'):
        if 'Argument' == neighbor.get('elementType'):
            for child in neighbor.iter('stringProp'):
                if child.attrib.get('name') == 'Argument.value':
                    currentArg = neighbor.attrib.get('name')
                    allParams[currentArg] = child.text
    return allParams

# Checks if string is not blank or empty
def isNotBlank (myString):
    if myString and myString.strip():
        #myString is not None AND myString is not empty or blank
        return True
    #myString is None OR myString is empty or blank
    return False

# Run it
if __name__ == '__main__':
    app.run(debug=True, port=8181,host= '0.0.0.0')
