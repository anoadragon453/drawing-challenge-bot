import logging

from nio import AsyncClient, MatrixRoom
from nio.events.room_events import RoomMessageText

from drawing_challenge_bot.chat_functions import send_text_to_room
from drawing_challenge_bot.config import Config

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(
        self,
        client: AsyncClient,
        config: Config,
        command: str,
        room: MatrixRoom,
        event: RoomMessageText,
    ):
        """A command made by a user

        Args:
            client: The client to communicate to matrix with
            config: Bot configuration parameters
            command: The command and arguments
            room: The room the command was sent in
            event: The event describing the command
        """
        self.client = client
        self.config = config
        self.room = room
        self.event = event

        msg_without_prefix = command[
            len(config.command_prefix) :
        ]  # Remove the cmd prefix
        self.args = (
            msg_without_prefix.split()
        )  # Get a list of all items, split by spaces
        self.command = self.args.pop(
            0
        )  # Remove the first item and save as the command (ex. `remindme`)

    async def process(self):
        """Process the command"""
        if self.command == "help":
            await self._help()

    async def _help(self):
        """Show the help text"""
        if not self.args:
            text = (
                "Hello, I am a bot! Use `help commands` to view available " "commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "commands":
            text = """
I post about weekly drawing challenges from /r/MLPDrawingSchool!
"""
        else:
            text = "Unknown help topic!"

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        """Computer says 'no'."""
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )
