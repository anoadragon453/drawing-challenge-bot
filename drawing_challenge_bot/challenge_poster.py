import logging
from datetime import datetime
from typing import List

from nio import AsyncClient
from praw import Reddit
from praw.reddit import Submission

from drawing_challenge_bot.chat_functions import send_text_to_room
from drawing_challenge_bot.config import Config
from drawing_challenge_bot.scraper import Scraper
from drawing_challenge_bot.storage import Storage

logger = logging.getLogger(__name__)


ONE_WEEK_IN_SECONDS = 60 * 60 * 24 * 7


class ChallengePoster:
    """"""

    def __init__(
        self, client: AsyncClient, config: Config, store: Storage, reddit: Reddit
    ):
        self.client = client
        self.config = config
        self.store = store
        self.reddit = reddit

        self.scraper = Scraper(config, store, reddit)

    async def scrape_and_post(self):
        """Scrapes the latest challenge posts and updates any rooms if necessary"""
        # Scrape latest challenge posts
        challenges = self.scraper.scrape()
        await self._update_rooms(challenges)

    async def _update_rooms(self, challenges: List[Submission]):
        """Posts the next challenge in a room if necessary

        Args:
            challenges: A list of challenge submissions

        """
        rooms = self.store.get_rooms()
        now_ts = datetime.utcnow().timestamp()

        logger.debug("Updating rooms...")

        for room_id, last_challenge_dict in rooms.items():
            last_post_timestamp = last_challenge_dict["posted_timestamp"]

            if (
                last_post_timestamp is not None
                and last_post_timestamp + ONE_WEEK_IN_SECONDS > now_ts
            ):
                # It hasn't been a week since we last posted in this room. Skip this room
                continue

            # Iterate through each challenge in order of date
            # Once we find a post that's newer than our last post
            # (and it's been at least 1 week since our last post in the room)
            # then post that challenge!
            for challenge in challenges:
                if last_post_timestamp and challenge.created_utc <= last_post_timestamp:
                    # We've already posted this one
                    continue

                # Found a new challenge to post!
                await self._post_challenge(room_id, challenge)

                # No need to keep searching through challenges for this room
                break

    async def _post_challenge(self, room_id: str, challenge: Submission):
        """Post a given challenge to a given room"""
        text = f"""
**New Art Challenge!**

*{challenge.title}*

{challenge.selftext}

[Link to original post]({challenge.url})"""

        logger.info("Posting challenge %s to room: %s", challenge.id, room_id)

        try:
            await send_text_to_room(self.client, room_id, text)
        except Exception as e:
            logger.error(
                "Unable to post challenge %s to room %s: %s", challenge.id, room_id, e
            )

        # Mark that we've posted this challenge
        self.store.upsert_challenge_for_room(room_id, challenge)
