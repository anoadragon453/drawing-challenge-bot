import logging
import re
from typing import List

from praw import Reddit
from praw.reddit import Submission

from drawing_challenge_bot.config import Config
from drawing_challenge_bot.storage import Storage

logger = logging.getLogger(__name__)


class Scraper:
    def __init__(self, config: Config, store: Storage, reddit: Reddit):
        self.config = config
        self.store = store
        self.reddit = reddit

        self.subreddit = self.reddit.subreddit("mlpdrawingschool")

        self.challenge_regex = re.compile(
            r'.*href="(http[^"]+)".*>.*Drawing Challenge.*<'
        )

    def scrape(self) -> List[Submission]:
        """Scrapes the subreddit wiki for any new challenges

        Returns:
            A list of challenges sorted from oldest post date to newest
        """
        logger.debug("Starting scrape")

        challenges = []

        # Get wiki page HTML
        wiki = self.subreddit.wiki["biweekly"]
        wiki_html_lines = wiki.content_html.split("\n")

        # Parse HTML for submissions
        for line in wiki_html_lines:
            match = self.challenge_regex.match(line)
            if match:
                # We found a challenge URL! Create a challenge Submission from it
                url = match.group(1)

                challenge = Submission(reddit=self.reddit, url=url)
                challenges.append(challenge)

        logger.debug("Scraping complete. Got %s challenges", len(challenges))

        # Sort submissions from oldest to newest
        challenges.sort(key=lambda c: c.created_utc)

        return challenges
