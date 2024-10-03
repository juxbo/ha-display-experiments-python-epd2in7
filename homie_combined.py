
from rpi_epd2in7.epd import EPD

from PIL import Image, ImageDraw, ImageFont, ImageOps
from gpiozero import Button
from threading import Event
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime, timedelta
from dotenv import load_dotenv

import requests
import locale
import os
import random
import csv

# CONFIGURE HOME ASSISTANT
load_dotenv()

token = os.getenv("HA_TOKEN")
base_url = os.getenv("HA_BASE_URL")
basedir = os.getenv("SCRIPT_BASEDIR")
cfg_locale = "de_DE.UTF-8"

# SETUP SENSORS AND STATE TO DISPLAY
rooms = {
    "Wohnzimmer": {
        "temp": "sensor.atc_1148_temperature",
        "light": "light.wohnzimmer"
    },
    "Schlafzimmer": {
        "temp": "sensor.atc_0095_temperature",
        "light": "light.schlafzimmer"
    },
    "Flur": {
        "temp": "sensor.hue_motion_sensor_1_temperature",
        "light": "light.flur"
    },
    "Balkon": {
        "temp": "sensor.atc_0d1c_temperature",
    },
}
rooms_state = {
    "Wohnzimmer": {
        "temp": "23.5",
        "light": "On"
    },
    "Schlafzimmer": {
        "temp": "21.0",
        "light": "Off"
    },
    "Flur": {
        "temp": "19.0",
        "light": "Off"
    },
    "Balkon": {
        "temp": "17.5",
    },
}

charsPerLine = 22
defaultBounce = 0.05
prob = 90
tarotbasedir = basedir + '/images/'
sleep_minutes = 5
now = datetime.now()

epd = EPD()
epd.init()
image = Image.new('1', (epd.width, epd.height), 255)
draw = ImageDraw.Draw(image)
start_tarot = Event()
exit_tarot = Event()

s = requests.Session()
retries = Retry(total=10,
                backoff_factor=1)
s.mount('http://', HTTPAdapter(max_retries=retries))

locale.setlocale(locale.LC_ALL, cfg_locale)

# LOAD TAROT IMAGES
deck = os.listdir(tarotbasedir)
print("Loaded %s card images" % len(deck))

# TODO: clean this globals mess up
choice = ""
is_upside_down = False
original_img = None

# TAROT FONTS
tarot_font = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf', 24)
tarot_fontItalic = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf', 16)
tarot_smallfont = ImageFont.truetype('/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf', 16)

# HA FONTS
boldfont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 24)
bigfont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 24)
smallfont = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
icons_font = ImageFont.truetype('/usr/local/share/fonts/fa6-Free-Solid-900.otf', 24)

# chars to use for icons
icons = {
    "bulb": u"\uf0eb",
    "temp-high": u"\uf2c7",
    "temp": u"\uf2c9",
    "test": u"\uf2cb",
}

def random_with_prob():
    nr = random.randint(1, 101)
    if nr <= prob:
        return True
    return False

def wrap_text(input_string, limit):
    words = input_string.split(' ')
    wrapped_text = ''
    current_line = ''

    for word in words:
        # Prüfen, ob das aktuelle Wort in die aktuelle Zeile passt
        if len(current_line) + len(word) + 1 <= limit:
            if current_line:
                current_line += ' ' + word
            else:
                current_line = word
        else:
            # Füge die aktuelle Zeile dem wrapped_text hinzu und starte eine neue Zeile
            wrapped_text += current_line + '\n'
            current_line = word

    # Füge die letzte Zeile hinzu
    if current_line:
        wrapped_text += current_line

    return wrapped_text

def draw_card_meaning(card_dict):
    global image
    global draw
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    
    name = wrap_text(card_dict['card_name'], 12)
    draw.multiline_text((0, 0), name, font=tarot_font, fill=0)
    box = draw.multiline_textbbox((0, 0), name, font=tarot_font)
    title_offset = box[3] + 5
    draw.line([0, title_offset, epd.width, title_offset], fill=0, width=2)

    # Draw the meanings
    if is_upside_down:
        box = draw_card_meaning_text(draw, "Bedeutung (umgekehrt):", card_dict['card_meaning_upsidedown'], title_offset + 5)
        draw_card_meaning_text(draw, "Bedeutung:", card_dict['card_meaning'], box[3] + 5)
    else:
        box = draw_card_meaning_text(draw, "Bedeutung:", card_dict['card_meaning'], title_offset + 5)
        draw_card_meaning_text(draw, "Bedeutung (umgekehrt):", card_dict['card_meaning_upsidedown'], box[3] + 5)

    epd.display_frame(image)

def draw_card_meaning_text(draw, label, meaning_text, initial_offset):
    meaning_wrapped = wrap_text(meaning_text, 18)
    
    # Draw label
    if initial_offset is not None:
        draw.text((0, initial_offset), label, font=tarot_fontItalic, fill=0)
        meaning_offset = initial_offset + 20
    else:
        # Calculate the position based on previous meaning box
        meaning_offset = draw.textbbox((0, 0), label, font=tarot_fontItalic)[3] + 2  # Update this to calculate correctly based on the previous drawn area

    # Draw meaning text
    draw.multiline_text((0, meaning_offset), meaning_wrapped, font=tarot_smallfont, fill=0)
    meaning_box = draw.multiline_textbbox((0, meaning_offset), meaning_wrapped, font=tarot_smallfont)
    
    return meaning_box

def display_card(choice, is_upside_down, filter=Image.NEAREST): 
    global image, original_img
    original_img == None
    
    with Image.open(tarotbasedir + choice) as im:
        image = im.resize((epd.width, epd.height), filter)
        if is_upside_down:
            image = image.rotate(180)
        epd.display_frame(image)
        epd.sleep()

def new_random_card_callback():
    global choice, is_upside_down
    print("Button1 - Tarot activated - Choosing new random card")
    start_tarot.set()
    
    # display should be in sleep mode, re-activating it
    init_display()
    choice = random.choice(deck)
    is_upside_down = not random_with_prob()
    display_card(choice, is_upside_down)

def show_card_details_callback():
    global image, original_img
    print("Button2 - Request to show tarot card details")

    if start_tarot.is_set() and len(choice) > 0:
        init_display(False)
        if original_img == None:
            # switch to details
            original_img = image
            card_dict = tarot_cards_dict[choice]
            print(choice)
            print(card_dict)
            draw_card_meaning(card_dict)
        else:
            # switch back to card
            image = original_img
            original_img = None
            epd.display_frame(image)
        epd.sleep()
    else:
        print("Tarot card not initialized")

def button_callback3():
    print("invert current image (for fun)")
    global image
    init_display(False)
    image = ImageOps.invert(image)
    epd.display_frame(image)
    epd.sleep()

def button_callback4():
    print("Going back to homie screen")
    exit_tarot.set()

def init_tarot():
    with open(basedir + 'card-meanings.csv', mode='r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            tarot_cards_dict[row['Dateiname']] = {
                'card_name': row['Name der Karte'],
                'card_meaning': row['Bedeutung der Karte'],
                'card_meaning_upsidedown': row['Bedeutung der Karte falls umgedreht']
            }
    print("Loaded %s card meanings" % len(tarot_cards_dict))

def init_buttons():
    print("Init buttons")
    global button1, button2, button3, button4
    button1 = Button(5, bounce_time=defaultBounce)
    button1.when_pressed = new_random_card_callback

    button2 = Button(6, bounce_time=defaultBounce)
    button2.when_pressed = show_card_details_callback

    button3 = Button(13, bounce_time=defaultBounce)
    button3.when_pressed = button_callback3

    button4 = Button(19, bounce_time=defaultBounce)
    button4.when_pressed = button_callback4

# HOMIE
def update_state():
    global now
    now = datetime.now()
    print(now)
    headers = {"Authorization": "Bearer " + token}

    for room in rooms:
        for sensor in rooms[room]:
            url = base_url + rooms[room][sensor]
            print(url)
            res = s.get(url, headers=headers)
            json = res.json()
            print(json['state'])
            rooms_state[room][sensor] = json['state']

def init_display(reset_img=True):
    global epd, image, draw
    epd.init()
    if reset_img:
        image = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(image)

# setup card meaning dict
tarot_cards_dict = {}

#update_state()
init_tarot()

init_display()
init_buttons()

pl = 4
lh = 24
icon_offset = 24

def draw_icon(choice, position):
    draw.text(position, icons[choice], font=icons_font)

def draw_centered_text(posY, text, font=bigfont):
    w = draw.textlength(text, font=font)
    draw.text(((epd.width-w)/2, posY), text, font=font, fill=0)

def draw_room(offsetY, name):
    room_light = rooms_state[name].get('light', None)
    room_temp = rooms_state[name].get('temp', None)

    draw.text((pl, offsetY), name, font=smallfont, fill=0)

    current_left_offset = pl
    if room_light:
        draw_icon("bulb", (pl, offsetY + lh))
        draw.text((icon_offset, offsetY + lh), room_light, font=smallfont, fill=0)
        current_left_offset = 60

    if room_temp:
        draw_icon("temp", (current_left_offset, offsetY + lh))
        draw.text((current_left_offset + icon_offset, offsetY + lh), "{:.1f}".format(float(room_temp)) + " °C", font=smallfont, fill=0)

    return offsetY + lh + lh

def clear_screen():
    image = Image.new('1', (epd.width, epd.height), 255)
    epd.display_frame(image)
    epd.sleep()

def draw_screen():
    global now, image
    init_display()
    print(now)
    draw_centered_text(0, now.strftime("%H:%M"), boldfont)
    draw_centered_text(26, now.strftime("%A %d.%m"), smallfont)
    draw.line([0, 26+24, epd.width, 26+24], fill=0, width=2)
    offset = draw_room(26+28, 'Wohnzimmer')
    offset = draw_room(offset, 'Flur')
    offset = draw_room(offset, 'Schlafzimmer')
    offset = draw_room(offset, 'Balkon')
    epd.display_frame(image)
    print("done drawing, sending display to sleep")
    epd.sleep()

clear_screen_next_loop = False
clear_times_every_x_hours = 4

# main loop
while True:
    # todo: startup, first update should be close to start of a minute so that time is correct
    print(start_tarot.is_set())
    if not start_tarot.is_set():
        if clear_screen_next_loop:
            clear_screen()
        print("updating state")
        update_state()
        draw_screen()

        # to keep time in-sync, calculate wait time until the next minute interval starts (+1 second leeway)
        current_time = datetime.now()
        minute = (current_time.minute - (current_time.minute % sleep_minutes)) % 60
        print("Current minute interval: %d" % minute)
        next_minute = current_time.replace(minute=minute, second=1, microsecond=0) + timedelta(minutes=sleep_minutes)
        wait = (next_minute-datetime.now()).seconds

        clear_screen_next_loop = minute == 0 and (current_time.hour % clear_times_every_x_hours) == 0
        print("waiting %s seconds" % wait)
        start_tarot.wait(wait)
    else:
        print("showing tarot - stopping home-assistant updates until user goes back to home")
        exit_tarot.wait()
        start_tarot.clear()
        exit_tarot.clear()

