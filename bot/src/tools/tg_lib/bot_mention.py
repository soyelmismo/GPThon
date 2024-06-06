command_list = ["/ask", "/rol", "/reset", "/select", "/retry", "/transcribe"]

from bot.src.tools.tg_lib.mini_tools import is_user

async def check(event):
    if event.message and event.message.mentioned: return True, "/ask"

    command = str(event.message.message).split(" ")[0].lower().strip()
    if "@" in command:
        command = command.split("@")[0].strip()
    try:
        media = event.message.media
        docc = bool(media and media.document)

        if is_user(event):
            if docc and not command: command = "/transcribe"
            if command not in command_list: command = "/ask"
            return True, command
        elif (not media and command in command_list) or (docc and command == "/transcribe"):
            return True, command
        else:
            return False, command

    except AttributeError:
        return True, command
