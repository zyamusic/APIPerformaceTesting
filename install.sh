if command -v python3 >/dev/null 2>&1 ; then
    echo "python3 found"
    echo "version: $(python3 --version)"
else
    echo "python3 not found, please install it"
    exit
fi

if command -v pip3 >/dev/null 2>&1 ; then
    echo "pip3 found"
else
    echo "pip3 not found, please install it"
    exit
fi

if command -v virtualenv >/dev/null 2>&1 ; then
    echo "virtualenv found"
else
    echo "virtualenv not found, please install it"
    pip3 install virtualenv
fi

if [ -d ~/.envs/APIPerf3 ]; then
  echo "~/.envs/APIPerf3 found"
else
  echo "Creating ~/.envs/APIPerf3 with virtual environment"
  virtualenv -p python3 ~/.envs/APIPerf3
fi

if [ ${VIRTUAL_ENV} ]
    then
        "Virtual environment found"
    else
      "Virtual environment not found, please source ~/.envs/APIPerf3/bin/activate"
      exit
fi

if command -v jmeter >/dev/null 2>&1 ; then
    echo "jmeter found"
else
    echo "jmeter not found, please download it and add it to your PATH"
    echo "http://jmeter.apache.org/download_jmeter.cgi"
    exit
fi

if [ -d ~/repos ]; then
  echo "~/repos found"
else
  echo "~/repos not found, creating..."
  mkdir ~/repos
fi

if [ -f ~/repos/APIPerformaceTesting/Source/keys.txt ]; then
  echo "keys.txt found"
else
  echo "keys.txt not found, ask Russell for the keys to Twitter to generate datasets using twitter feeds"
  touch ~/repos/APIPerformaceTesting/Source/keys.txt
fi

if [ -d ~/repos/DittyAudioContent ]; then
  echo "~/repos/DittyAudioContent found"
else
  echo "~/repos/DittyAudioContent not found, please clone the repo"
  echo "run git clone https://github.com/zyamusic/DittyAudioContent.git and provide your credentials"
fi

echo "Starting server install"
cd ~/repos/APIPerformaceTesting/Source
pip install -r requirements.txt
python app.py &
echo "Server Running"
