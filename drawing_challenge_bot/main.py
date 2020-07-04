#!/usr/bin/env python3

import asyncio
import logging
import sys
from datetime import datetime, timedelta
from time import sleep

import praw
from aiohttp import ClientConnectionError, ServerDisconnectedError
from apscheduler.schedulers import SchedulerAlreadyRunningError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LocalProtocolError,
    LoginError,
    RoomMemberEvent,
    RoomMessageText,
)

from drawing_challenge_bot.callbacks import Callbacks
from drawing_challenge_bot.challenge_poster import ChallengePoster
from drawing_challenge_bot.config import Config
from drawing_challenge_bot.storage import Storage

logger = logging.getLogger(__name__)


async def main():
    # Read config file

    # A different config file path can be specified as the first command line arg
    if len(sys.argv) > 1:
        config_filepath = sys.argv[1]
    else:
        config_filepath = "config.yaml"
    config = Config(config_filepath)

    # Set up reddit API
    reddit = praw.Reddit(
        client_id=config.client_id,
        client_secret=config.client_secret,
        user_agent=config.user_agent,
    )

    # Configure storage
    store = Storage(config, reddit)

    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    # Initialize the matrix client
    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        store_path=config.store_path,
        config=client_config,
    )

    # Set up event callbacks
    callbacks = Callbacks(client, store, config)
    client.add_event_callback(callbacks.message, (RoomMessageText,))
    client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
    client.add_event_callback(callbacks.member_event, (RoomMemberEvent,))

    # Set up a scheduler
    scheduler = AsyncIOScheduler()

    # Set up a challenge poster
    challenge_poster = ChallengePoster(client, config, store, reddit)

    # Add a job that checks for new challenges every minute
    trigger = IntervalTrigger(
        seconds=60, start_date=datetime.now() + timedelta(seconds=2),
    )

    # Add the scrape and update job
    scheduler.add_job(challenge_poster.scrape_and_post, trigger=trigger)

    # Keep trying to reconnect on failure (with some time in-between)
    while True:
        try:
            # Try to login with the configured username/password
            try:
                login_response = await client.login(
                    password=config.user_password, device_name=config.device_name,
                )

                # Check if login failed. Usually incorrect password
                if type(login_response) == LoginError:
                    logger.error("Failed to login: %s", login_response.message)
                    logger.warning("Trying again in 15s...")

                    # Sleep so we don't bombard the server with login requests
                    sleep(15)
                    continue
            except LocalProtocolError as e:
                # There's an edge case here where the user hasn't installed the correct C
                # dependencies. In that case, a LocalProtocolError is raised on login.
                logger.fatal(
                    "Failed to login. Have you installed the correct dependencies? "
                    "https://github.com/poljar/matrix-nio#installation "
                    "Error: %s",
                    e,
                )
                return False

            # Login succeeded!

            # Sync encryption keys with the server
            # Required for participating in encrypted rooms
            if client.should_upload_keys:
                await client.keys_upload()

            logger.info(f"Logged in as {config.user_id}")
            logger.info("Startup complete")

            # Allow jobs to fire
            try:
                scheduler.start()
            except SchedulerAlreadyRunningError:
                pass

            await client.sync_forever(timeout=30000, full_state=True)

        except (ClientConnectionError, ServerDisconnectedError, TimeoutError):
            logger.warning("Unable to connect to homeserver, retrying in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        except Exception as e:
            logger.warning("Unknown exception occurred: %s", e)
            logger.warning("Restarting in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        finally:
            # Make sure to close the client connection on disconnect
            await client.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
