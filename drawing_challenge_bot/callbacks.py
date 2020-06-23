import logging

from nio import AsyncClient, InviteMemberEvent, JoinError, MatrixRoom, RoomMemberEvent

from drawing_challenge_bot.bot_commands import Command
from drawing_challenge_bot.chat_functions import send_text_to_room
from drawing_challenge_bot.config import Config
from drawing_challenge_bot.errors import CommandError
from drawing_challenge_bot.storage import Storage

logger = logging.getLogger(__name__)


class Callbacks(object):
    """Callback methods that fire on certain matrix events

    Args:
        client: nio client used to interact with matrix
        store: Bot storage
        config: Bot configuration parameters
    """

    def __init__(
        self, client: AsyncClient, store: Storage, config: Config,
    ):
        self.client = client
        self.store = store
        self.config = config
        self.command_prefix = config.command_prefix

        # A little hack to work around the fact that matrix-nio calls invite() twice when
        # we receive an invite for some reason
        self.joined_rooms = {}

    async def message(self, room, event):
        """Callback for when a message event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """
        # Extract the message text
        msg = event.body

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        # Check whether this is a command
        if not msg.startswith(self.command_prefix):
            return

        logger.debug("Command received: %s", msg)

        # Assume this is a command and attempt to process
        command = Command(self.client, self.config, msg, room, event,)

        try:
            await command.process()
        except CommandError as e:
            # An expected error occurred. Inform the user
            msg = f"Error: {e.msg}"
            await send_text_to_room(self.client, room.room_id, msg)

            # Print traceback
            logger.exception("CommandError while processing command:")
        except Exception as e:
            # An unknown error occurred. Inform the user
            msg = f"An unknown error occurred: {e}"
            await send_text_to_room(self.client, room.room_id, msg)

            # Print traceback
            logger.exception("Unknown error while processing command:")

    async def invite(self, room: MatrixRoom, event: InviteMemberEvent):
        """Callback for when an invite is received. Join the room specified in the invite"""

        if room.room_id in self.joined_rooms:
            # Skip this invite. Workaround hack explained in this class' constructor
            del self.joined_rooms[room.room_id]
            return

        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                logger.info(f"Joined {room.room_id}")
                break
        else:
            logger.error("Unable to join room: %s", room.room_id)
            return

        # Note that we've joined this room
        self.joined_rooms[room.room_id] = True
        self.store.upsert_challenge_for_room(room.room_id, challenge=None)

        # Wait for the room state to sync
        await self.client.sync()

        # Greet the room with a friendly message
        await self._greet_room(room.room_id)

    async def _greet_room(self, room_id: str):
        """Say hello to a new room"""
        text = """
Hello! I'm a bot that posts weekly art challenges from /r/MLPDrawingSchool!

In a moment, I'll post the first one. Then, a week later I'll post another one.
I'll keep doing this until I run out of challenges. But fear not, as more are
posted to /r/MLPDrawingSchool, I'll continue to post them here!

Have fun, and happy drawing /)^3^(\\\\!
        """

        try:
            await send_text_to_room(self.client, room_id, text)
        except Exception as e:
            logger.error("Unable to send greeting to room %s: %s", room_id, e)

    async def member_event(self, room: MatrixRoom, event: RoomMemberEvent):
        """A membership event occurred"""
        if event.membership == "kick" or event.membership == "ban":
            logger.info(
                "We got a %s from room %s, deleting room entry",
                event.membership,
                room.room_id,
            )
            self._kick_or_ban(room.room_id)

    def _kick_or_ban(self, room_id: str):
        """When we're kicked or banned, delete the entry for the room"""
        self.store.delete_room_entry(room_id)
