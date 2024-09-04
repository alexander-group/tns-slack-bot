"""
just some configuration constants 
"""
import numpy as np
import os

TNS_CLASSES_OF_INTEREST = np.array([
    "TDE",
    "TDE-H",
    "TDE-He",
    "TDE-H-He"
])

SLACK_BOT_TOKEN = os.environ.get("TNS_SLACK_BOT_TOKEN", None)
if SLACK_BOT_TOKEN is None:
    raise ValueError("You have not set the environment variable 'TNS_SLACK_BOT_TOKEN'")

CHANNEL = "alexander-group"

BOT_NAME = "TNS TDE Bot"
