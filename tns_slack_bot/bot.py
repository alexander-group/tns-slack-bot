"""
The actual TNS bot
"""
import os
import time
import datetime
from .tns_helpers import download_daily_csv
from .config import *
import pandas as pd
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord
from slack_sdk import WebClient

class TNSSlackBot(WebClient):

    def __init__(self, dt=1, daily_data_path="tns_public_objects.csv", **kwargs):
        """
        Args:
            dt (float) : The delta t to look for new classifications in, in days.
                         Default is in the last day
            daily_data_path (str) : The path to write the daily TNS csv to
        """

        
        self.dt = dt*u.day
        if (
                not os.path.exists(daily_data_path) or
                (time.time()-os.path.getmtime(daily_data_path)) > self.dt.value
        ):
            print("Downloading new file...")
            self.daily_data_path = download_daily_csv(daily_data_path)
        else:
            print("File found and is recent enough to keep...")
            self.daily_data_path = daily_data_path
            
        self.daily_data = pd.read_csv(self.daily_data_path, skiprows=1)

        super().__init__(token=SLACK_BOT_TOKEN, **kwargs)
        
    def filter_daily_data(self):
        """
        Filters down the massive daily data release from TNS to only the new data
        that we care about
        """

        transient_modify_date = Time(
            self.daily_data.lastmodified.values.tolist(),
            format="iso"
        )
        now = Time(datetime.datetime.now(tz=datetime.timezone.utc), scale='utc')
        
        self.daily_data['dt'] = now - transient_modify_date
        self.daily_data['isTDE'] = np.isin(
            self.daily_data.type,
            TNS_CLASSES_OF_INTEREST
        )
        
        return self.daily_data[self.daily_data.isTDE * (self.daily_data.dt < self.dt)]

    def generate_slack_message(self, filtered_df):
        """
        Generate a slack message to send based on the results of the above filtering
        """

        if len(filtered_df) == 0:
            out = "No new transients of interest found of the following TNS types:\n"
            for item in TNS_CLASSES_OF_INTEREST:
                out += f"\t-{item}\n"
            return out
        
        out = f"""
The following transients of interest ({", ".join(TNS_CLASSES_OF_INTEREST)}) were recently modified in the last {self.dt.value} days on the TNS:

        """

        for i, row in filtered_df.iterrows():
            out += f"""
Name: {row.name_prefix} {row['name']}
\tAlternate Names: {row.internal_names}
\tClassified Type: {row.type}
\tCoordinates: {SkyCoord(row.ra, row.declination, unit='deg').to_string('hmsdms')}
\tRedshift: {row.redshift}
\tTNS Link: https://www.wis-tns.org/object/{row['name']}
\tDiscovery ADS Bibcode: {row.Discovery_ADS_bibcode}
\tClassification ADS Bibcode: {row.Class_ADS_bibcodes}
\n
        """
        
        return out

    def send_slack_message(self, chan="testing", uname="TNS TDE Bot"):
        todays_new_data = self.filter_daily_data()
        msg = self.generate_slack_message(todays_new_data)
        self.chat_postMessage(channel=chan, text=msg, username=uname)
