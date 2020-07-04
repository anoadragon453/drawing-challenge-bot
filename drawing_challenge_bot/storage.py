import logging
from datetime import datetime
from typing import Dict, Optional, Union

from praw.reddit import Submission, Reddit

from drawing_challenge_bot.config import Config

latest_migration_version = 1

logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, config: Config, reddit: Reddit):
        """Setup the database

        Runs an initial setup or migrations depending on whether a database file has already
        been created

        Args:
            config: The bot config. config.database must be a dictionary containing
                the following keys:
                    * type: A string, one of "sqlite" or "postgres"
                    * connection_string: A string, featuring a connection string that
                        be fed to each respective db library's `connect` method
        """
        self.config = config
        self.reddit = reddit

        # Check which type of database has been configured
        self.conn = self._get_database_connection(
            config.database["type"], config.database["connection_string"]
        )
        self.cursor = self.conn.cursor()
        self.db_type = config.database["type"]

        # Try to check the current migration version
        migration_level = 0
        try:
            self._execute("SELECT version FROM migration_version")
            row = self.cursor.fetchone()
            migration_level = row[0]
        except Exception:
            self._initial_db_setup()
        finally:
            if migration_level < latest_migration_version:
                self._run_db_migrations(migration_level)

        logger.info(f"Database initialization of type '{self.db_type}' complete")

    def _get_database_connection(self, database_type: str, connection_string: str):
        if database_type == "sqlite":
            import sqlite3

            # Initialize a connection to the database, with autocommit on
            return sqlite3.connect(connection_string, isolation_level=None)
        elif database_type == "postgres":
            import psycopg2

            conn = psycopg2.connect(connection_string)

            # Autocommit on
            conn.set_isolation_level(0)

            return conn

    def _execute(self, *args):
        """A wrapper around cursor.execute that transforms ?'s to %s for postgres"""
        if self.db_type == "postgres":
            self.cursor.execute(args[0].replace("?", "%s"), *args[1:])
        else:
            self.cursor.execute(*args)

    def _initial_db_setup(self):
        """Initial setup of the database"""
        logger.info("Performing initial database setup...")

        # Set up the migration_version table
        self._execute(
            """
            CREATE TABLE migration_version (
                version INTEGER PRIMARY KEY
            )
        """
        )

        # Initially set the migration version to 0
        self._execute(
            """
            INSERT INTO migration_version (
                version
            ) VALUES (?)
        """,
            (0,),
        )

        self._execute(
            """
            CREATE TABLE room_post (
                -- The ID of the Matrix room that this was posted in
                room_id TEXT PRIMARY KEY,
                -- The ID of the last posted challenge
                last_challenge_id TEXT,
                -- When the challenge was posted to the room
                posted_timestamp BIGINT
            )
        """
        )

        self._execute(
            """
            CREATE UNIQUE INDEX room_id
            ON room_post(room_id)
        """
        )

    def _run_db_migrations(self, current_migration_version: int):
        """Execute database migrations. Migrates the database to the
        `latest_migration_version`

        Args:
            current_migration_version: The migration version that the database is
                currently at
        """
        logger.debug("Checking for necessary database migrations...")

        if current_migration_version < 1:
            logger.info("Migrating the database from v0 to v1...")

            # There was a bug that preventing any challenges other than the first from being
            # posted.
            # https://github.com/anoadragon453/drawing-challenge-bot/issues/1
            self._execute(
                """
                ALTER TABLE room_post
                ADD COLUMN
                reddit_posted_timestamp BIGINT
            """
            )

            # Get the date of when each post in the database was created on reddit
            self._execute(
                """
                SELECT last_challenge_id FROM room_post
                """
            )
            post_ids = [row[0] for row in self.cursor.fetchall()]

            # Deduplicate post IDs and iterate through each
            for post_id in set(post_ids):
                # Lookup the post
                post = self.reddit.submission(id=post_id)

                # Save the creation timestamp
                self._execute("""
                    UPDATE room_post SET reddit_posted_timestamp = ? WHERE last_challenge_id = ?
                """, (post.created_utc, post_id))

            self._execute(
                """
                 UPDATE migration_version SET version = 1
            """
            )
            logger.info("Database migrated to v1")

    def get_rooms(self) -> Dict[str, Dict[str, Union[str, int, int]]]:
        """Get the last post information for each known room"""
        self._execute(
            """
            SELECT room_id, last_challenge_id, posted_timestamp, reddit_posted_timestamp
            FROM room_post
        """
        )

        # Return dictionary of room_id to challenge information
        return {
            row[0]: {
                "last_challenge_id": row[1],
                "posted_timestamp": row[2],
                "reddit_posted_timestamp": row[3],
            }
            for row in self.cursor.fetchall()
        }

    def upsert_challenge_for_room(
        self, room_id: str, challenge: Optional[Submission] = None
    ):
        """Upsert latest challenge for a given room

        Args:
            room_id: The id of the room to modify
            challenge: The challenge submission to use the details of. If None, a row will
                be created for the room with no challenge details. We would do this if the
                bot is in the room, but hasn't posted a challenge yet.
        """
        last_challenge_id = challenge.id if challenge else None
        posted_timestamp = datetime.utcnow().timestamp() if challenge else None
        reddit_posted_timestamp = challenge.created_utc if challenge else None

        self._execute(
            """
            INSERT INTO room_post
                (room_id, last_challenge_id, posted_timestamp, reddit_posted_timestamp)
                VALUES (?, ?, ?, ?)
            ON CONFLICT(room_id) DO
                UPDATE SET
                    last_challenge_id = ?,
                    posted_timestamp = ?,
                    reddit_posted_timestamp = ?
                WHERE room_id = ?
        """,
            (
                room_id,
                last_challenge_id,
                posted_timestamp,
                reddit_posted_timestamp,
                last_challenge_id,
                posted_timestamp,
                reddit_posted_timestamp,
                room_id,
            ),
        )

    def delete_room_entry(self, room_id: str):
        """Delete an entry in the room_post table"""
        self._execute(
            """
            DELETE FROM room_post WHERE room_id = ?
        """,
            (room_id,),
        )
