"""
Helper functions for the TNS Slack Bot
"""

# imports
import os
import zipfile
import requests
import json
import time
from copy import deepcopy
from collections import OrderedDict

def set_bot_tns_marker():
    tns_marker = (
        'tns_marker{"tns_id": '
        + str(os.environ["TNS_BOT_ID"])
        + ', "type": "bot", "name": "'
        + str(os.environ["TNS_BOT_NAME"])
        + '"}'
    )
    return tns_marker

def download_daily_csv(outfile="tns_public_objects.csv"):
    """
    Download the TNS daily CSV
    """

    # url to the daily staging of all TNS objects
    url = "https://www.wis-tns.org/system/files/tns_public_objects/"
    url += "tns_public_objects.csv.zip"

    # create the download header
    tns_marker = set_bot_tns_marker()
    headers = {"User-Agent": tns_marker}

    # put the api key in the data
    data = {"api_key": os.environ["TNS_API_KEY"]}

    # request the download
    response = requests.post(url, headers=headers, data=data)

    # write output to a zip file
    if response.status_code == 200:
        # this means it succeeded!
        outzip = outfile + ".zip"
        with open(outzip, "wb") as f:
            f.write(response.content)

    else:
        raise ValueError(
            f"Downloading the TNS Daily CSV Failed with Code {response.status_code}"
        )

    # unzip the outfile
    with zipfile.ZipFile(outzip, "r") as z:
        z.extractall(os.getcwd())

    # return the output file for ease later
    return outfile
    
