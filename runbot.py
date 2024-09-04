"""
CLI for running the slack bot through python
"""
from tns_slack_bot import TNSSlackBot
from astropy import units as u
import argparse
import logging

logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(filename="tns-slack-bot.log")
    
    p = argparse.ArgumentParser()
    p.add_argument("--delta_t", "-dt", required=False, help="The delta time in days to filter by", default=1)
    p.add_argument("--outfile", "-o", required=False, help="The filepath to write the TNS dataset to", default="tns_public_objects.csv")
    args = p.parse_args()

    logger.info("Initializing Slack Bot...")
    try:
        bot = TNSSlackBot(dt=float(args.delta_t)*u.day, daily_data_path=args.outfile)
    except Exception as e:
        logger.exception(e)

    logger.info("Finished Initializing the Slack Bot!")
    logger.info("Attempting to send the slack message...")
    try:
        bot.send_slack_message()
    except Exception as e:
        logger.exception(e)
    logger.info("Sent the slack message successfully!")
    
if __name__ == "__main__":
    main()
