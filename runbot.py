"""
CLI for running the slack bot through python
"""
import os
from tns_slack_bot import TNSSlackBot
from astropy import units as u
import argparse
import logging

logger = logging.getLogger(__name__)
def main():

    FILE_DIR = os.path.dirname(os.path.realpath(__file__))
    
    p = argparse.ArgumentParser()
    p.add_argument(
        "--delta_t", "-dt",
        required=False,
        help="The delta time in days to filter by",
        default=1
    )
    p.add_argument(
        "--outfile", "-o",
        required=False,
        help="The filepath to write the TNS dataset to",
        default="tns_public_objects.csv"
    )

    p.add_argument(
        "--log", "-l",
        required=False,
        help="The filepath to write the log to",
        default="tns-slack-bot.log"
    )

    p.add_argument(
        "--test",
        action=argparse.BooleanOptionalAction,
        help="If true, just prints the message instead of sending it"
    )
    
    args = p.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(message)s',
        datefmt='%m/%d/%Y %I:%M:%S %p',
        filename=args.log,
        encoding='utf-8',
        level=logging.DEBUG
    )


    logger.info("Initializing Slack Bot...")
    try:
        bot = TNSSlackBot(dt=float(args.delta_t), daily_data_path=args.outfile)
    except Exception as e:
        logger.exception(e)

    logger.info("Finished Initializing the Slack Bot!")
    logger.info("Attempting to send the slack message...")
    try:
        bot.send_slack_message(test=args.test)
    except Exception as e:
        logger.exception(e)
    
if __name__ == "__main__":
    main()
