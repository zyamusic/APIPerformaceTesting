import os
import re
import csv
import glob
import json
import time
import shutil
import codecs
# import tweepy
import urllib.request, urllib.parse, urllib.error
import itertools as itt
import xml.etree.ElementTree as ET
from werkzeug import secure_filename
from flask import Flask,render_template, redirect, url_for, request

###########TWITTER
# keyFile = open('keys.txt', 'r')
# consumer_key = keyFile.readline().rstrip()
# consumer_secret = keyFile.readline().rstrip()
# access_key = keyFile.readline().rstrip()
# access_secret = keyFile.readline().rstrip()
###########TWITTER

app = Flask(__name__)

############ BASE CONFIG ###########
JMETER = 'jmeter'
jmeterLog = 'jmeter.log'
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

shiftOptions           = ['4', '5','6','7','8']
threadedOptions        = ['0','1']
bypassOptions          = ['0','1']
SubprocOptions         = ['0','1']
globalSelectedMic      = 'all'
globalTwitterUser      = 'theRealDonaldTrump'
globalDataUsing        = 'CSV_Data_File.csv'
globalDataUsingForward = 'CSV_Data_FileForward.csv'
globalDataUsingReverse = 'CSV_Data_FileReverse.csv'
saltDataText           = 'swag'

jMeterArgs = {}
############ BASE CONFIG ###########

############ Init Folders ###########
direc = 'static/Config'
if not os.path.exists(direc):
    os.makedirs(direc)

direc = 'static/Data'
if not os.path.exists(direc):
    os.makedirs(direc)

direc = 'static/Output'
if not os.path.exists(direc):
    os.makedirs(direc)

############ Init Folders ###########

# Homepage
@app.route('/')
@app.route('/index')
def index():
    # update test params
    global allParams
    allParams = GetNewJMX()

    # display all summary files
    summaries = GetSummaries()

    return render_template('index.html', summaries=summaries, allParams=allParams,currentDataset=globalDataUsing,saltDataText=saltDataText)

# Testing area
@app.route('/executeTest', methods=['GET','POST'])
def executeTest():
    global OUTPUT
    global allParams
    global globalDataUsing
    global saltDataText
    if request.method == 'GET':
        allParams = GetNewJMX()
        summaries = GetSummaries()

        return render_template('index.html', summaries=summaries, allParams=allParams)

    else:
        # Get test params
        for arg,val in allParams.items():
            print(arg)
            jMeterArgs[arg] = request.form[arg]

        originalCFG = jMeterArgs['out_cfg']

        timestr = time.strftime("%d-%m-%y_%H:%M:%S")
        jMeterArgs['time_run'] = timestr

        # Check if running permutations
        runVars = request.form.get('RunVariations')
        saltDataChk = request.form.get('SaltDataset')
        if saltData:
            saltDataText = request.form['SaltDatasetText']
            # find out how many rows are needed and provide them to the salter
            numLines = 2 * int( jMeterArgs['num_Dittys'], 10 ) * 4 # int( jMeterArgs['thread_count'], 10 )
            saltData(saltDataText, numLines )
            jMeterArgs['out_cfg'] += saltDataText

            OUTPUT = 'static/Output/' + jMeterArgs['out_cfg']
        else:
            OUTPUT = 'static/Output/' + jMeterArgs['out_cfg']

        if runVars:
            runVariations()
        else:
            # Update configs values
            print('making conifg')
            tree = ET.parse(CONFIG)
            root = tree.getroot()
            for neighbor in root.iter('elementProp'):
                if 'Argument' == neighbor.get('elementType'):
                    for child in neighbor.iter('stringProp'):
                        if child.attrib.get('name') == 'Argument.value':
                            currentArg = neighbor.attrib.get('name')
                            child.text = jMeterArgs[currentArg]
                            print(neighbor.attrib.get('name') + ' = ' + child.text)

            tree.write(CONFIG)

            # prepare outut strings
            OUTPUT += '/' + jMeterArgs['time_run']
            OUTPUT += '/' + jMeterArgs['num_Dittys'] + 'Dittys'

            OUTPUT_HTML = OUTPUT + '/HTML'
            OUTPUTFile = OUTPUT + '.csv'

            os.makedirs(OUTPUT_HTML)

            RunJMeter(CONFIG, OUTPUTFile, OUTPUT_HTML, True)

            jMeterArgs['out_cfg'] = originalCFG

        return redirect(url_for('index'))

# Configure the dataset
@app.route('/configData', methods=['GET','POST'])
def configData():
    # Get mic ids for form'
    allMics = getAllMicIDs()
    datasets = GetDatasets()

    if request.method == 'GET':
        return render_template('configData.html', datasets=datasets, allMics=allMics)

    else:
        selectedMicID = request.form['MicID']
        tweetUser = request.form['TwitterUser']
        tweetCount = request.form['TweetCount']

        globalSelectedMic = selectedMicID
        globalTwitterUser = tweetUser

        # Prepare dataset
        alltweets = getAllTweets(tweetUser,tweetCount)
        allSongs = getAllSongs(selectedMicID)
        dataPairs = []
        for permutation in itt.product(alltweets,allSongs):
            dataPairs.append(permutation)

        # Write dataset
        writeDataFile(dataPairs, selectedMicID, tweetUser, tweetCount)

        return redirect(url_for('index'))

# Upload a new configuration
@app.route('/upload_jmx', methods=['GET','POST'])
def upload_jmx():
    global allParams
    print('UPLOADING')

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

# Upload a new configuration
@app.route('/upload_data', methods=['POST'])
def upload_data():
    global globalDataUsing

    switchData = request.form.get('dataset')
    timestr = time.strftime("%H%M%S")
    if switchData:
        globalDataUsing = switchData
        shutil.copy(os.getcwd() + '/CSV_Data_File.csv',os.getcwd() + '/static/Data/' + timestr + '_'+switchData)
        shutil.copy(os.getcwd() + '/static/Data/' + switchData, os.getcwd() + '/CSV_Data_File.csv')
        shutil.copy(os.getcwd() + '/static/Data/' + switchData, os.getcwd() + '/static/CSV_Data_File.csv')
    else:
        # Save old versions and update for new config
        # Put in static folder to serve them over http
        f = request.files['file']
        f.save(secure_filename(f.filename))

        globalDataUsing = f.filename

        shutil.copy(os.getcwd() + '/CSV_Data_File.csv',os.getcwd() + '/static/Data/' + timestr + '_CSV_Data_File.csv')
        shutil.copy(f.filename, os.getcwd() + '/CSV_Data_File.csv')
        shutil.copy(f.filename, os.getcwd() + '/static/CSV_Data_File.csv')

    return redirect(url_for('configData'))

@app.route('/log', methods=['GET'])
def log():
    logData = getLogData()
    return render_template('Log.html',logData=logData)

# Get all songs based on mic id
def getAllSongs(micID):
    songs = []
    for item in [d for d in os.listdir(SONGS) if os.path.isdir(os.path.join(SONGS, d))]:
        if not item.startswith('.'):
            jsonFile = SONGS + '/' + item + '/' + item + '.json'
            if os.path.exists(jsonFile):
                with codecs.open(jsonFile,'r',encoding='utf-8') as file:
                    if 'all' in micID:
                        songs.append(item.encode('utf-8'))
                    elif any(micID in line for line in file):
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
                            if isNotBlank(mic):
                                mics.add(mic)
    return mics

# Get a specified number of tweets from a twitter user
def getAllTweets(screen_name, tweetCount):
    # tweetCount = int(tweetCount)
    tweetText = []
    # #Twitter only allows access to a users most recent 3240 tweets with this method

    # #authorize twitter, initialize tweepy
    # auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    # auth.set_access_token(access_key, access_secret)
    # api = tweepy.API(auth)

    #initialize a list to hold all the tweepy Tweets
    # alltweets = []

    #make initial request for most recent tweets (200 is the maximum allowed count)
    # if tweetCount > 200:
    #     new_tweets = api.user_timeline(screen_name = screen_name,count=200)
    #     #save most recent tweets
    #     alltweets.extend(new_tweets)
    #     oldest = alltweets[-1].id - 1

    #     #keep grabbing tweets until there are no tweets left to grab
    #     while len(new_tweets) > 0 and len(alltweets) < tweetCount:

    #         #all subsiquent requests use the max_id param to prevent duplicates
    #         new_tweets = api.user_timeline(screen_name = screen_name,count=200,max_id=oldest)

    #         #save most recent tweets
    #         alltweets.extend(new_tweets)

    #         #update the id of the oldest tweet less one
    #         oldest = alltweets[-1].id - 1

    # else:
    #     new_tweets = api.user_timeline(screen_name = screen_name,count=tweetCount)
    #     alltweets.extend(new_tweets)

    # for tweet in alltweets:
    #     if len(tweetText) <= tweetCount:
    #         tweetText.append(tweet.text)
    return tweetText

# Writes the dataset of (text,song)
def writeDataFile(pairs, micId, twitterUser, tweetCount):
    global globalDataUsing

    csv_data_file_name = "static/Data/" + micId + "_" +twitterUser + "_" + tweetCount + "Data.csv"
    globalDataUsing = csv_data_file_name[12:]

    with open( csv_data_file_name, 'w' ) as csvfile:
        for p in pairs:
            t,s=p
            text = urllib.parse.quote_plus( t )
            song = urllib.parse.quote_plus(s)
            text = re.sub(r"http\S+", "", text) # Remove http links
            if isNotBlank(text) and isNotBlank(song):
                csvfile.write( text + "," + song + "\n" )

    shutil.copy(csv_data_file_name, os.getcwd() + '/CSV_Data_File.csv')
    shutil.copy(csv_data_file_name, os.getcwd() + '/static/CSV_Data_File.csv')

# Runs all permutations of perfrmance tests
def runVariations ():
    allCombos = itt.product(shiftOptions, threadedOptions, bypassOptions, SubprocOptions)

    for shift,thread,bypass,subproc in allCombos:
        jMeterArgs['shiftBufferBy'] = shift
        jMeterArgs['writeOnBgThread'] = thread
        jMeterArgs['bypassOGGEncoding'] = bypass
        jMeterArgs['useSubProcess'] = subproc

        if subproc == '0' and bypass == '0':
            print('Unneccessary run')
        else:
            tree = ET.parse(CONFIG)
            root = tree.getroot()
            for neighbor in root.iter('elementProp'):
                if 'Argument' == neighbor.get('elementType'):
                    for child in neighbor.iter('stringProp'):
                        if child.attrib.get('name') == 'Argument.value':
                            currentArg = neighbor.attrib.get('name')
                            child.text = jMeterArgs[currentArg]
                            print(neighbor.attrib.get('name') + ' = ' + child.text)

            tree.write(CONFIG)

            timestr = time.strftime("%Y%m%d-%H%M%S")
            OUTPUT += '_' + jMeterArgs['out_cfg']
            OUTPUT += '_' + jMeterArgs['num_Dittys'] + 'Dittys'
            # for arg, val in allParams.iteritems():
            #     OUTPUT += '_' + arg[0] + jMeterArgs[arg]

            OUTPUT_HTML = OUTPUT + '_HTML'
            OUTPUTFile = OUTPUT + '.csv'

            RunJMeter(CONFIG, OUTPUTFile, OUTPUT_HTML, False)
            # print JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML
            #
            # os.system(JMETER + ' -n -t ' + CONFIG + ' -l ' + OUTPUTFile + ' -e -o ' + OUTPUT_HTML)
        print('starting next permutation')

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
    return allParams #adfadsf adsfasdfadsfadfssasdf

def RunJMeter(configPath, outputFile, outputHTML, asDaemon):
    print (outputFile)
    zipDir = outputFile[:-4]
    print (' && zip -r ' + zipDir + '.zip ' + zipDir)
    cmd = JMETER + ' -n -t ' + configPath + ' -l ' +outputFile + ' -e -o ' + outputHTML + ' && zip -r ' + zipDir + '.zip ' + zipDir

    if asDaemon:
        cmd = cmd + ' &'

    # Run jmeter command
    print(cmd)
    os.system(cmd)

def GetSummaries():
    print( "GettingSummaries" )
    list_summaries = []
    summaries = {}
    indexfiles = glob.glob('static/Output/**/HTML/index.html', recursive=True )
    print( " found " + str( len( indexfiles ) ) + " indexfiles" )
    os.system( 'pwd' )
    outFiles = sorted( indexfiles, key=os.path.getmtime, reverse=True )
    print( " found " + str( len( outFiles ) ) + " outFiles" )
    if outFiles is not None:
        print( "found outFiles" )
        for outFile in outFiles:
            parts = outFile.split('/') # os.pathsep
            # static/Output/goodbye_LavNam/25-05-17_17:05:11/100Dittys/uno
            part_lengths = list( map( len, parts ) )
            pals = zip( part_lengths, list( parts ))
            print( list( pals ) )

            stop_At = sum( part_lengths[:4] )
            print ("stop_At " + str( stop_At ) )
            summaries = {}
            print( "now Procesing:" + outFile )
            # outKey = outFile[14:] # Magic numbers 
            print ( "prefix = " + outFile[:stop_At] )
            zipFile = ''
            for fl in glob.iglob(outFile[:stop_At]+'*/**/*.zip', recursive=True):
                zipFile = fl # why the loop? we should be able to just get the file directly

            for overallFL in glob.iglob(outFile[:stop_At]+'*/*.csv', recursive=True):
                overallCSV = overallFL
                summaries['overall'] = overallCSV

            for newFL in glob.iglob(outFile[:stop_At]+'*/**/opt*/*.csv', recursive=True):
                newCSV = newFL
                summaries['new'] = newCSV

            for oldFL in glob.iglob(outFile[:stop_At]+'*/**/unopt*/*.csv', recursive=True):

                oldCSV = oldFL
                summaries['old'] = oldCSV

            summaries['zip'] = zipFile

            reportPath = '/' + outFile
            summaries['report'] = reportPath

            lastColon = outFile.rfind(':')
            description , run_on = outFile[:lastColon+3].replace('static/Output/','').split('/')            
            summaries['description'] = description
            summaries['run_on'] = run_on 

            list_summaries.append(summaries)

    return list_summaries

def GetDatasets():
    datasets = {}
    for outFile in glob.iglob('static/Data/*.csv'):
        outKey = outFile[12:]
        datasets[outKey] = '/' + outFile
    return datasets

def getLogData():
    logData = []
    if os.path.exists(jmeterLog):
        with open(jmeterLog, 'r') as logFile:
            logData = logFile.readlines()


    return reversed(logData)

def saltData(saltText, numLines = -1 ):
    global globalDataUsing
    dataFile = globalDataUsing

    dataset = open(dataFile , 'r')

    newLines = []
    for idx,line in enumerate( dataset ):
        if ( -1 != numLines and idx >= numLines ):
            break

        cols = line.split(',')
        salted = re.sub('(?<=\*)(.*?)(?=\*)',saltText, cols[0])
        newLines.append(salted + ',' + cols[1])
    dataset.close()

    #clear out file
    #open(dataFile,'w').close()

    forward = open(globalDataUsingForward , 'w')
    for line in newLines:
        forward.write(line)
    forward.close()

    reverse = open(globalDataUsingReverse , 'w')
    for line in reversed(newLines):
        reverse.write(line)
    reverse.close()

    return

def make_tree(path):
    tree = dict(name=path, children=[])
    try: lst = os.listdir(path)
    except OSError:
        pass #ignore errors
    else:
        for name in lst:
            fn = os.path.join(path, name)
            if os.path.isdir(fn):
                tree['children'].append(make_tree(fn))
            else:
                tree['children'].append(dict(name=fn))
    return tree

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
