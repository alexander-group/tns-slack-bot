"""
The actual TNS bot
"""
import os
import time
import logging
from io import StringIO
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup
from .tns_helpers import download_daily_csv
from .config import *
import pandas as pd
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord
from slack_sdk import WebClient

logger = logging.getLogger(__name__)

class TNSSlackBot(WebClient):

    def __init__(self, dt=1, daily_data_path="tns_public_objects.csv", **kwargs):
        """
        Args:
            dt (float) : The delta t to look for new classifications in, in days.
                         Default is in the last day
            daily_data_path (str) : The path to write the daily TNS csv to
        """

        
        self.dt = dt*u.day
        file_mod_date = os.path.getmtime(daily_data_path)
        file_dt_s = time.time() - file_mod_date
        file_dt_days = file_dt_s / (60*60*24)
        if (
                not os.path.exists(daily_data_path) or
                file_dt_days > self.dt.value
        ):
            logger.info("Downloading new file...")
            self.daily_data_path = download_daily_csv(daily_data_path)
        else:
            logger.info("File found and is recent enough to keep...")
            self.daily_data_path = daily_data_path
            
        self.daily_data = pd.read_csv(self.daily_data_path, skiprows=1)

        # generate the astronote search URL
        now = datetime.now()
        dt = timedelta(days=self.dt.value)
        qdate = now-dt
        qdate_strfmt = f"{qdate.year}-{qdate.month}-{qdate.day}"
        self.astronote_url = f"https://www.wis-tns.org/astronotes?&date_start%5Bdate%5D={qdate_strfmt}"
        
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
        now = Time(datetime.now(tz=timezone.utc), scale='utc')
        
        self.daily_data['dt'] = now - transient_modify_date
        self.daily_data['isTDE'] = np.isin(
            self.daily_data.type,
            TNS_CLASSES_OF_INTEREST
        )
        
        return self.daily_data[self.daily_data.isTDE * (self.daily_data.dt < self.dt)]

    def query_astronotes(self):
        """
        Queries the astronote search page for recent TDE-related astronotes
        """
        # download the raw HTML
        hdr = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}
        res = requests.get(self.astronote_url, headers=hdr)

        soup = BeautifulSoup(res.content.decode(), "lxml")

        astronotes = soup.find_all(class_="note")
        t = TNS_CLASSES_OF_INTEREST
        
        new_astronotes = f"""
*New Astronotes of Potential Interest*
*###########################################*
"""
        tde_astronotes = []
        for a in astronotes:
            r = a.find(string="TDE")
            if r is None: continue
            tde_astronotes.append(r)
            
            partial_link = a.find(class_="note-link").get("href")        
            link = f"https://www.wis-tns.org{partial_link}"
            authors = a.find(class_="note-coauthors").get_text()
            title = a.find(class_="note-title").get_text()
            
            new_astronotes += f"""

>_Title_: {title}
>_Authors_: {authors}
>_Link_: {link}
>-------------------------------------------"""
            
            note = requests.get(link, headers=hdr).content.decode()
            subsoup = BeautifulSoup(note, "lxml")

            tab = subsoup.find(class_="objects-table")
            df = pd.read_html(StringIO(str(tab)))[0]

            # only take TDEs
            # if "Candidate Type"
            class_names = []
            if "Reported Obj-Type" in df:
                class_names.append("Reported Obj-Type")
            if "TNS Obj-Type" in df:
                class_names.append("TNS Obj-Type")
            if "Candidate type" in df:
                class_names.append("Candidate type")

            filt = df[class_names].isin(t).sum(axis=1).astype(bool)
            df = df[filt]

            for _, row in df.iterrows():
                row = row.dropna()
                #print(row)
                name = row.Name

                ra, dec = None, None
                if "TNS RA" in row and "TNS DEC" in row:
                    ra = row["TNS RA"]
                    dec = row["TNS DEC"]
                elif "Reported RA" in row and "Reported Dec" in row:
                    ra = row["Reported RA"]
                    dec = row["Reported DEC"]

                classification = None
                for pkey in ["Reported Obj-Type", "TNS Obj-Type", "Candidate type"]:
                    if pkey in row:
                        classification = row[pkey]

                if classification not in t: continue

                redshift = None
                for col in row.keys():
                    if "Redshift" in col:
                        redshift = row[col]
                        
                new_astronotes += f"""
>\t_Name_: {name}
>\t_Coordinates_: ({ra}, {dec})
>\t_Classification_: {classification}
>\t_Redshift_: {redshift}
>*******************************************"""

        if len(tde_astronotes) == 0:
            return ""
                
        return new_astronotes
                
    def generate_slack_message(self, filtered_df):
        """
        Generate a slack message to send based on the results of the above filtering
        """

        if len(filtered_df) == 0:
            return ""
            
        out = f"""
*Recent Object Modification*
*###########################################*
\n"""

        for i, row in filtered_df.iterrows():
            out += f"""
>_Name_: {row.name_prefix} {row['name']}
>\t_Alternate Names_: {row.internal_names}
>\t_Classified Type_: {row.type}
>\t_Coordinates_: {SkyCoord(row.ra, row.declination, unit='deg').to_string('hmsdms')}
>\t_Redshift_: {row.redshift}
>\t_TNS Link_: https://www.wis-tns.org/object/{row['name']}
>\t_Discovery ADS Bibcode_: {row.Discovery_ADS_bibcode}
>\t_Classification ADS Bibcode_: {row.Class_ADS_bibcodes}
"""
        
        return out

    def send_slack_message(self, chan=CHANNEL, uname=BOT_NAME, test=False):
        todays_new_data = self.filter_daily_data()
        msg1 = self.generate_slack_message(todays_new_data)
        msg2 = self.query_astronotes()
        
        msg = msg1 + "\n" + msg2

        if len(msg1) == 0 and len(msg2) == 0:
            logger.info(
                f"No new TNS updates from the past {int(self.dt.value)} days!"
            )
            return

        logger.info(msg)
        if test:
            print(msg)
            return

        self.chat_postMessage(channel=chan, text=msg, username=uname)
        
