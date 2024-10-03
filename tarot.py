from rpi_epd2in7.epd import EPD
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps

from gpiozero import Button
from signal import pause

import os
import random
import csv

basedir = os.getcwd() + '/cards'
charsPerLine = 22
defaultBounce = 0.05
prob = 90

# setup card meaning dict
tarot_cards_dict = {}

with open('card-meanings.csv', mode='r', encoding='utf-8') as file:
    csv_reader = csv.DictReader(file)
    for row in csv_reader:
        tarot_cards_dict[row['Dateiname']] = {
            'card_name': row['Name der Karte'],
            'card_meaning': row['Bedeutung der Karte'],
            'card_meaning_upsidedown': row['Bedeutung der Karte falls umgedreht']
        }

print("Loaded %s card meanings" % len(tarot_cards_dict))

# debug: print all cards
# for dateiname, details in tarot_cards_dict.items():
#     print(f"{dateiname}: {details}")

# setup display
epd = EPD()
epd.init()
empty_img = Image.new('1', (epd.width, epd.height), 255)

image = empty_img
draw = ImageDraw.Draw(image)

font = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-BoldItalic.ttf', 24)
fontItalic = ImageFont.truetype('/usr/share/fonts/truetype/liberation2/LiberationSerif-Italic.ttf', 16)
smallfont = ImageFont.truetype('/usr/share/fonts/truetype/quicksand/Quicksand-Bold.ttf', 16)

deck = os.listdir(basedir)
print("Loaded %s card images" % len(deck))

# TODO: omg clean this globals mess up
choice = ""
is_upside_down = False
original_img = None

def random_with_prob():
    nr = random.randint(1, 101)
    if nr <= prob:
        return True
    return False

# check if probability is working (yes)
# count_true = 0
# for lp in range(100):
#     guess = random_with_prob()
#     if guess:
#         count_true = count_true + 1
# print(count_true)

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
    image = ImageOps.invert(image)
    epd.display_partial_frame(image, 0, 0, epd.height, epd.width, fast=True)
    image = Image.new('1', (epd.width, epd.height), 255)
    draw = ImageDraw.Draw(image)
    
    name = wrap_text(card_dict['card_name'], 12)
    draw.multiline_text((0, 0), name, font=font, fill=0)
    box = draw.multiline_textbbox((0, 0), name, font=font)
    title_offset = box[3] + 5
    draw.line([0, title_offset, epd.width, title_offset], fill=0, width=2)

    # meaning_offset = title_offset + 5
    # meaning_wrapped = wrap_text(card_dict['card_meaning'], 18)
    # draw.text((0, meaning_offset), "Bedeutung:", font=fontItalic, fill=0)
    # draw.multiline_text((0, meaning_offset + 20), meaning_wrapped, font=smallfont, fill=0)
    # meaning_box = draw.multiline_textbbox((0, meaning_offset + 20), name, font=font)
    
    # new_offset = meaning_box[3] + 2
    # upside_wrapped = wrap_text(card_dict['card_meaning_upsidedown'], 18)
    # draw.text((0, new_offset), "Bedeutung (umgekehrt):", font=fontItalic, fill=0)
    # draw.text((0, new_offset + 20), upside_wrapped, font=smallfont, fill=0)

    # epd.display_frame(image)

    # Draw the meanings
    if is_upside_down:
        box = draw_card_meaning_text(draw, "Bedeutung (umgekehrt):", card_dict['card_meaning_upsidedown'], title_offset + 5)
        draw_card_meaning_text(draw, "Bedeutung:", card_dict['card_meaning'], box[3] + 5)
    else:
        box = draw_card_meaning_text(draw, "Bedeutung:", card_dict['card_meaning'], title_offset + 5)
        draw_card_meaning_text(draw, "Bedeutung (umgekehrt):", card_dict['card_meaning_upsidedown'], box[3] + 5)

    # in theory it might be possible to speed up the page switch with something like this:
    # image = ImageOps.invert(image)
    # epd.display_partial_frame(image, 0, 0, epd.height, epd.width, fast=True)
    # image = ImageOps.invert(image)
    # epd.display_partial_frame(image, 0, 0, epd.height, epd.width, fast=True)
    
    epd.display_frame(image)

def draw_card_meaning_text(draw, label, meaning_text, initial_offset):
    meaning_wrapped = wrap_text(meaning_text, 18)
    
    # Draw label
    if initial_offset is not None:
        draw.text((0, initial_offset), label, font=fontItalic, fill=0)
        meaning_offset = initial_offset + 20
    else:
        # Calculate the position based on previous meaning box
        meaning_offset = draw.textbbox((0, 0), label, font=fontItalic)[3] + 2  # Update this to calculate correctly based on the previous drawn area

    # Draw meaning text
    draw.multiline_text((0, meaning_offset), meaning_wrapped, font=smallfont, fill=0)
    meaning_box = draw.multiline_textbbox((0, meaning_offset), meaning_wrapped, font=smallfont)
    
    return meaning_box

def display_card(choice, is_upside_down, filter=Image.NEAREST): 
    global image
    global original_img
    original_img == None
    
    with Image.open("cards/"+choice) as im:
        image = im.resize((epd.width, epd.height), filter)
        if is_upside_down:
            image = image.rotate(180)
            # maybe invert image for dramatic effect
            # image = ImageOps.invert(image)
        epd.display_frame(image)

def new_random_card_callback():
    global image
    global choice
    global is_upside_down

    print("Choosing new random card")
    choice = random.choice(deck)
    is_upside_down = not random_with_prob()
    display_card(choice, is_upside_down)

def show_card_details_callback():
    global original_img
    global image

    if len(choice) > 0:
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
    else:
        print("no card yet")

def button_callback3():
    print("invert current image (for fun)")
    global image
    image = ImageOps.invert(image)
    epd.display_frame(image)

current_filter_index = 0
available_filters = [Image.NEAREST, Image.BILINEAR, Image.BICUBIC, Image.LANCZOS]
filter_names = ["nearest", "bilinear", "bicubic", "lanczos"]

def button_callback4():
    global image
    global choice
    global is_upside_down
    global current_filter_index
    print("re-draw using filter %s" % filter_names[current_filter_index])
    display_card(choice, is_upside_down, available_filters[current_filter_index])
    current_filter_index = (current_filter_index + 1) % len(available_filters)


button1 = Button(5, bounce_time=defaultBounce)
button1.when_pressed = new_random_card_callback

button2 = Button(6, bounce_time=defaultBounce)
button2.when_pressed = show_card_details_callback

button3 = Button(13, bounce_time=defaultBounce)
button3.when_pressed = button_callback3

button4 = Button(19, bounce_time=defaultBounce)
button4.when_pressed = button_callback4

pause()