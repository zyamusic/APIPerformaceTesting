# APIPerformaceTesting
Flask application to run JMeter tests against an api server

## Requirements
To install and run the app, ensure you have
  * [jmeter](http://jmeter.apache.org/download_jmeter.cgi) installed and accessible on your ```$PATH```
  * [Python 3.*](https://www.python.org/downloads/release/)
  * virtualenv installed from pip
    * pip install virtaulenv
  * Create a virtualenv ``` virtualenv ~/.envs/APIPerf3 ```
  * [DittyAudioContent](https://github.com/zyamusic) repo in the same directory as the APIPerformanceTesting repo
    * git clone https://github.com/DittyAudioContent.git
  * Twitter api key file ```keys.txt``` in ```.../APIPerformanceTesting/Source```

  ### Installation
  * Source your virtualenv ``` source ~/.ens/APIPerf3/bin/activate ```
  *  Make sure to have done all the steps in the requirements then run ``` sh install.sh ```

## Usage
To run the app, cd to the Source folder and run ```python app.py``` The webserver will be listening on [YourIP:8181 externally or localhost:8181](http://localhost:8181)

> ### Index
> This page lists all html reports in the ```Source/static/Output``` folder and allows the user to start a new test run with the form on the right side.

> ### Configure Dataset
> Here you can create a new dataset to use based on a mic id and tweets from a specific user.

> ### Upload a new jmx
> This allows you to change the config of the tests being run.
