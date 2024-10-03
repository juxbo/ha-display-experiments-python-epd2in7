from rpi_epd2in7.epd import EPD
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from twitch_chat_irc import twitch_chat_irc
from dotenv import load_dotenv

import os

load_dotenv()

oauth = os.getenv("TWITCH_TOKEN")
user = os.getenv("TWITCH_USER")
channel = "twitch"
charsPerLine = 22

epd = EPD()
epd.init()

image = Image.new('1', (epd.width, epd.height), 255)
draw = ImageDraw.Draw(image)

font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
smallfont = ImageFont.truetype('/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf', 16)

draw.multiline_text((0,5), 'Connecting:\n' + channel, font=font, fill=0)
epd.smart_update(image)

msg_count = 1
offset = 50

def drawMessage(message):
    global msg_count
    global offset
    global image
    global draw
    if offset > epd.height:
        resetChat()
    else:
        msg_count = msg_count + 1
    print(message)
    draw.text((0, offset), message['display-name'], font=font, fill=0)
    msgTuple = breakMsg(message['message'])
    draw.multiline_text((0, offset + 20), msgTuple[0], font=smallfont, fill=0)
    offset = offset + 24 + msgTuple[1]
    print(offset)
    epd.smart_update(image)

def breakMsg(text):
    lines = 1
    textOffset = charsPerLine
    newText = text[:textOffset] + "\n"
    while textOffset < len(text):
        newOffset = textOffset+charsPerLine
        partialText = text[textOffset:newOffset].lstrip()
        newText = newText + partialText + "\n"
        textOffset = newOffset
        lines = lines + 1
    print(newText)
    print(lines)
    return [newText, lines*19]

def resetChat():
    global image
    global draw
    global offset
    global msg_count
    offset = 0
    msg_count = 0
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    epd.display_frame(image)

#resetChat()
connection = twitch_chat_irc.TwitchChatIRC(user, oauth)
messages = connection.listen(channel, on_message=drawMessage)
