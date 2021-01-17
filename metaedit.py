import asyncio
import json
import os
import shutil
import tkinter as tk
from os import walk
from pathlib import Path
from tkinter import filedialog

import piexif as piexif
# import pyheif
from PIL import ImageTk, Image
from PIL.ExifTags import TAGS
from PIL.TiffImagePlugin import IFDRational

win = tk.Tk()
win.geometry('1200x800')  # set window size

panel = tk.Label(win)
panel.grid(row=0, column=0, columnspan=3, rowspan=12, padx=0, pady=0)

###############
# Global Vars #
###############

# tags used in EXIF metadata
# source: https://www.tranquillitybase.jp/PME/userguide/taggedFormat_en.html
exif_tags = {
    36880: "Offset Time",
    36881: "Offset Time Original",
    36882: "Offset Time Digitized",
    42080: "Composite Image",
    # 100000: "TEST"
}

# custom current photo attribute prefixes
curr_people_prefix = "People:\t"
curr_location_prefix = "Location:\t"
curr_date_prefix = "Date:\t"
curr_group_prefix = "Group:\t"
curr_comment_prefix = "Comments:\t"

# set global values so that these can be cleared
people_sv = None
location_sv = None
date_sv = None
group_sv = None
comment_sv = None

people_entry = None
location_entry = None
date_entry = None
group_entry = None
comment_entry = None

# set global version so that these can be live updated for reflecting data back to the user
curr_people_label = None
curr_location_label = None
curr_date_label = None
curr_group_label = None
curr_comment_label = None

# search filters
filter_people_entry = None
filter_location_entry = None
filter_date_entry = None
filter_group_entry = None
filter_comment_entry = None

# used to control whether we write input/filter results or whether changes are from a photo switch
change_img_was_clicked = False  # loading image metadata
change_filter_was_clicked = False  # filtering

images = []

# Set defaults that increase based upon viewed images -- this prevents us from cutting images off in the viewer
max_scaled_height = 500
max_img_width = 0
max_img_height = 0

curr_img_path = None

# controls our iteration through all available images
curr_img_idx = -1

# 1. all images are read in and imagedescription field is retained as dict with key being image filename
# 2. on insert, dict is updated for given image filename to reflect inserted/changed data
# 3. search iterates through all image dicts, looking for matches
# store ImageDescription fields for filtering
indexed_images = {}

# global filter variables
filter_people = []
filter_location = ""
filter_date = ""
filter_group = ""
filter_comment = ""

# UI rendered element to show all matching image files
filterbox_lb = None

# global to track all images being dispalyed in filterbox and availble for export (matching filters applied)
filtered_images = []


###########
# Helpers #
###########
def clear_entries():
    global curr_img_idx, change_img_was_clicked, people_entry, location_entry, date_entry, \
        group_entry, comment_entry, curr_people_label, curr_location_label, curr_date_label, \
        curr_group_label, curr_comment_label, change_filter_was_clicked, filter_people_entry, \
        filter_location_entry, filter_date_entry, filter_group_entry, filter_comment_entry, \
        filter_people, filter_location, filter_date, filter_group, filter_comment

    # clear global search variables
    filter_people = []
    filter_location = ""
    filter_date = ""
    filter_group = ""
    filter_comment = ""

    # input fields
    if people_entry.get():
        change_img_was_clicked = True
        people_entry.delete(0, "end")
    if location_entry.get():
        change_img_was_clicked = True
        location_entry.delete(0, "end")
    if date_entry.get():
        change_img_was_clicked = True
        date_entry.delete(0, "end")
    if group_entry.get():
        change_img_was_clicked = True
        group_entry.delete(0, "end")
    if comment_entry.get():
        change_img_was_clicked = True
        comment_entry.delete(0, "end")

    # current image fields (existing data)
    curr_people_label.configure(text=curr_people_prefix)
    curr_location_label.configure(text=curr_location_prefix)
    curr_date_label.configure(text=curr_date_prefix)
    curr_group_label.configure(text=curr_group_prefix)
    curr_comment_label.configure(text=curr_comment_prefix)

    # search filters
    if filter_people_entry.get():
        change_filter_was_clicked = True
        filter_people_entry.delete(0, "end")
    if filter_location_entry.get():
        change_filter_was_clicked = True
        filter_location_entry.delete(0, "end")
    if filter_date_entry.get():
        change_filter_was_clicked = True
        filter_date_entry.delete(0, "end")
    if filter_group_entry.get():
        change_filter_was_clicked = True
        filter_group_entry.delete(0, "end")
    if filter_comment_entry.get():
        change_filter_was_clicked = True
        filter_comment_entry.delete(0, "end")

    # show all photos in filter results
    filter_images("", None)


async def index_images():
    global indexed_images

    for img_filename in images:
        # parse image file
        image = get_parsed_img(img_filename)
        if image is None:
            print(f"[ERROR] Failed to parse image [{img_filename}] while indexing images.")
            continue

        # get exif data out of image
        exif_data = image.getexif()

        indexed_images[img_filename] = {}

        # ImageDescription field is set for image and contains a dictionary object
        if piexif.ImageIFD.ImageDescription in exif_data:
            try:
                # extract ImageDescription field using metadata code
                img_desc_parsed = json.loads(exif_data[piexif.ImageIFD.ImageDescription])

                if 'location' in img_desc_parsed:
                    indexed_images[img_filename]['location'] = img_desc_parsed['location'].strip()
                if 'date' in img_desc_parsed:
                    indexed_images[img_filename]['date'] = img_desc_parsed['date'].strip()
                if 'group' in img_desc_parsed:
                    indexed_images[img_filename]['group'] = img_desc_parsed['group'].strip()
                if 'comment' in img_desc_parsed:
                    indexed_images[img_filename]['comment'] = img_desc_parsed['comment'].strip()
                if 'people' in img_desc_parsed:
                    people_set = set()
                    people_list = img_desc_parsed['people'].split(",")
                    for person in people_list:
                        people_set.add(person.strip())
                    indexed_images[img_filename]['people'] = people_set
            except json.decoder.JSONDecodeError as e:
                print(
                    f"[ERROR] Failed to decode image description [{img_filename}]. "
                    f"Setting fields to empty for filtering purposes."
                )


####################
# Parse image file #
####################
def get_parsed_img(img):
    # fixme: this processing doesn't work... heif_file.metadata or heif_file.data works properly,
    #  but the Image.frombytes() call fails to retain/parse the metadata :(
    try:
        # if img[-4:].lower() in ['heic', 'avif']:
        #     print(f"\nProcessing file [{img}] as heic or avif file...")
        #     heif_file = pyheif.read(img)
        #     image = Image.frombytes(
        #         heif_file.mode,
        #         heif_file.size,
        #         heif_file.data,
        #         "raw",
        #         heif_file.mode,
        #         heif_file.stride,
        #     )
        if img[-3:].lower() in ['jpg', 'jpeg']:
            # print(f"\nProcessing file [{img}] as jpg, JPG, JPEG file...")
            # read the image data using PIL
            image = Image.open(img)
        else:
            print(f"\n[ERROR] Failed to identify file [{img}]")
            return None
        return image
    except Exception as e:
        print(f"[ERROR] Failed to open file [{img}] with error:\n\n {e}")


##############################
# Resize image to fit screen #
##############################
def resize_img(image):
    global max_scaled_height, max_img_width, max_img_height
    # if image height > width, then it is a vertically taken picture and PIL rotates it so rotate it back
    if image.size[0] > image.size[1]:
        image = image.rotate(270)

    scaled_height = image.size[1] / max_scaled_height

    new_width = int(image.size[0] / scaled_height)
    new_height = int(image.size[1] / scaled_height)

    # update maximum image sizes
    if new_width > max_img_width:
        max_img_width = new_width
    if new_height > max_img_height:
        max_img_height = new_height

    image = image.resize((new_width, new_height), Image.ANTIALIAS)
    return image


#############################
# Image Loading and Display #
#############################
def display_updated_photo_attributes(image_desc_dict: dict):
    global curr_people_label, curr_location_label, curr_date_label, curr_group_label, curr_comment_label
    if 'people' in image_desc_dict:
        if isinstance(image_desc_dict['people'], str):
            curr_people_label.configure(text=curr_people_prefix + image_desc_dict['people'])
        else:
            # list case (multiple people in photo)
            screen_str = curr_people_prefix + ', '.join(image_desc_dict['people'][:-1]) + image_desc_dict['people'][-1]
            curr_people_label.configure(text=screen_str)
    if 'location' in image_desc_dict:
        curr_location_label.configure(text=curr_location_prefix + image_desc_dict['location'])
    if 'date' in image_desc_dict:
        curr_date_label.configure(text=curr_date_prefix + image_desc_dict['date'])
    if 'group' in image_desc_dict:
        curr_group_label.configure(text=curr_group_prefix + image_desc_dict['group'])
    if 'comment' in image_desc_dict:
        curr_comment_label.configure(text=curr_comment_prefix + image_desc_dict['comment'])


def load_img(display_image):
    global max_scaled_height, max_img_width, max_img_height, curr_img_path

    # parse image file
    image = get_parsed_img(display_image)
    if image is None:
        print(f"[ERROR] Failed to parse image [{display_image}]")
        return

    # update path since we were able to parse the image
    curr_img_path = display_image

    # resize image to fit screen
    image = resize_img(image)

    #############################
    # Set image for Tkinter GUI #
    #############################

    tk_image = ImageTk.PhotoImage(image)
    panel.img = tk_image  # keep a reference so it's not garbage collected
    panel['image'] = tk_image
    panel.config(height=max_scaled_height + 50, width=max_img_width + 50)

    #####################
    # extract EXIF data #
    #####################

    exif_data = image.getexif()

    parsed_data = {}

    # iterating over all EXIF data fields
    for tag_id in exif_data:
        # get the tag name, instead of human unreadable tag id
        tag = TAGS.get(tag_id, tag_id)

        # skip these tags as they are unwieldy
        if tag in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename',
                   'MakerNote'):
            continue
        elif tag in exif_tags.keys():
            tag = exif_tags.get(tag)

        data = exif_data.get(tag_id)
        # decode bytes
        if isinstance(data, bytes):
            data = data.decode()
        elif isinstance(data, int) or isinstance(data, str) or isinstance(data, tuple):
            data = data
        elif isinstance(data, IFDRational):
            ifdr = IFDRational(data)
            data = str(ifdr.numerator) + "/" + str(ifdr.denominator)
        else:
            print(f"[ERROR] Invalid metadata tag [{tag}] and tag_id [{tag_id}]: [{data}] with type [{type(data)}]")
            continue
        parsed_data[tag] = data

    # update current image attributes on UI
    if 'ImageDescription' in parsed_data:
        curr_photo_image_desc = json.loads(parsed_data['ImageDescription'])
        display_updated_photo_attributes(curr_photo_image_desc)


###########################
# insert custom EXIF data #
###########################
def write_input(text, data_key):
    # note: this gets called on every key press while user is focused in any input box
    global curr_img_path, curr_people_label, curr_location_label, curr_date_label, curr_group_label, \
        curr_comment_label, change_img_was_clicked, indexed_images

    # ignore change so that we don't overwrite data in the photo
    if change_img_was_clicked:
        change_img_was_clicked = False
        return

    img_desc = {
        "people": [],
        "location": "",
        "date": "",
        "group": "",
        "comment": ""
    }

    # todo: AUTOCOMPLETE
    #   - https://stackoverflow.com/questions/58428545/clarify-functionality-of-tkinter-autocomplete-entry

    exif_dict = piexif.load(curr_img_path)
    # create paths if they do not exist
    # update them if they do
    if '0th' in exif_dict:
        if piexif.ImageIFD.ImageDescription in exif_dict['0th']:
            # check if value is a btyes string and attempt to decode to json
            # if it is not our scheme, overwrite as empty dictionary (this is our metadata tag!)
            if isinstance(exif_dict['0th'][piexif.ImageIFD.ImageDescription], bytes):
                try:
                    curr_desc = json.loads(exif_dict['0th'][piexif.ImageIFD.ImageDescription].decode('ascii'))
                except Exception as e:
                    # e.g. was: b'Processed with VSCO with b1 preset'
                    print(f"[ERROR] Failed to decode binary string object for [{curr_img_path}]")
                    curr_desc = {}
            else:
                curr_desc = json.loads(exif_dict['0th'][piexif.ImageIFD.ImageDescription])
        else:
            exif_dict['0th'][piexif.ImageIFD.ImageDescription] = {}
            curr_desc = {}
    else:
        exif_dict['0th'] = {
            piexif.ImageIFD.ImageDescription: {}
        }
        curr_desc = {}
    if data_key in img_desc:
        text_data = text.get().strip()
        if data_key == "people":
            people_to_write = text_data.split(",")
            people_list_to_write = [person.strip() for person in people_to_write]
            curr_desc[data_key] = people_list_to_write
            if people_entry.get():
                curr_people_label.configure(text=curr_people_prefix + text_data)
            if data_key in indexed_images[curr_img_path]:
                people_set = set()
                [people_set.add(person) for person in people_list_to_write]
                indexed_images[curr_img_path][data_key] = people_set
        if data_key == "location":
            curr_desc[data_key] = text_data
            if location_entry.get():
                curr_location_label.configure(text=curr_location_prefix + text_data)
        if data_key == "date":
            curr_desc[data_key] = text_data
            if date_entry.get():
                curr_date_label.configure(text=curr_date_prefix + text_data)
        if data_key == "group":
            curr_desc[data_key] = text_data
            if group_entry.get():
                curr_group_label.configure(text=curr_group_prefix + text_data)
        if data_key == "comment":
            curr_desc[data_key] = text_data
            if comment_entry.get():
                curr_comment_label.configure(text=curr_comment_prefix + text_data)
        else:
            curr_desc[data_key] = text_data

        # already covered the special people set case above
        if data_key != "people" and data_key in indexed_images[curr_img_path]:
            indexed_images[curr_img_path][data_key] = text_data

    # dump updated dictionary as value into exif object
    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = json.dumps(curr_desc)

    # overwrite photo exif data
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, curr_img_path)


#############
# Filtering #
#############
def filter_images(text, text_type):
    global indexed_images, filter_people, filter_location, filter_date, filter_group, filter_comment, \
        filterbox_lb, filtered_images

    filterbox_lb.delete('0', 'end')

    if text_type is not None:
        # convert from tkinter StringVar to string or list
        text = text.get().strip()

    # update globals based upon changing text; leave other filters as previously set
    # this function is not responsible for clearing input on image change
    if len(text) > 0:
        if text_type == "people":
            people_to_filter = text.split(",")
            filter_people = [person.strip().lower() for person in people_to_filter]
        if text_type == "location":
            filter_location = text.lower()
        if text_type == "date":
            filter_date = text.lower()
        if text_type == "group":
            filter_group = text.lower()
        if text_type == "comment":
            filter_comment = text.lower()

    box_idx = 0

    # require full matches or empty filter variables
    filtered_images = []
    for image, image_data in indexed_images.items():
        location_match = filter_location == "" or (
                'location' in image_data and filter_location in image_data['location'].lower())
        date_match = filter_date == "" or ('date' in image_data and filter_date in image_data['date'].lower())
        group_match = filter_group == "" or ('group' in image_data and filter_group in image_data['group'].lower())
        comment_match = filter_comment == "" or (
                'comment' in image_data and filter_comment in image_data['comment'].lower())
        if len(filter_people) > 0 and 'people' not in image_data:
            people_match = False
        else:
            people_match = True
        # don't do this work if the simple matches failed or people are being filtered for
        if people_match and location_match and date_match and group_match and comment_match:
            for person in filter_people:
                lowercase_people = [p.lower() for p in image_data['people']]
                if person not in lowercase_people:
                    people_match = False
                    break

        if people_match and location_match and date_match and group_match and comment_match:
            filterbox_lb.insert(box_idx, image)
            filtered_images.append(image)
            box_idx += 1


#############
# Exporting #
#############
def export_images():
    new_directory = "filtered_images"
    try:
        os.mkdir(new_directory)
    except FileExistsError:
        shutil.rmtree(new_directory)
    os.mkdir(new_directory)
    for image_filename in filtered_images:
        shutil.copy2(image_filename, new_directory + "/" + image_filename)


################
# Control Flow #
################
def prev_img():
    global curr_img_idx
    if curr_img_idx - 1 < 0:
        return  # if there are no previous images, do nothing
    else:
        # advance one image in list
        curr_img_idx -= 1
        # get the next image in the list
        next_image = images[curr_img_idx]
        clear_entries()

    load_img(next_image)


def next_img():
    global curr_img_idx, people_sv, location_sv, date_sv, people_entry, location_entry, date_entry
    if curr_img_idx + 1 >= len(images):
        return  # if there are no more images, do nothing
    else:
        # advance one image in list
        curr_img_idx += 1
        # get the next image in the list
        next_image = images[curr_img_idx]
        clear_entries()

    load_img(next_image)


def display_editor():
    global curr_people_label, curr_location_label, curr_date_label, curr_group_label, curr_comment_label, \
        people_sv, location_sv, date_sv, group_sv, comment_sv, \
        people_entry, location_entry, date_entry, group_entry, comment_entry

    # create vertical scrollbar
    # see: https://www.youtube.com/watch?v=0WafQCaok6g
    # scroller = tk.Scrollbar(win)

    # create label widgets
    people_label = tk.Label(win, text="People")
    location_label = tk.Label(win, text="Location")
    date_label = tk.Label(win, text="Date")
    group_label = tk.Label(win, text="Group")
    comment_label = tk.Label(win, text="Comments")
    # -- display current photo metadata
    curr_people_label = tk.Label(win, text=curr_people_prefix)
    curr_location_label = tk.Label(win, text=curr_location_prefix)
    curr_date_label = tk.Label(win, text=curr_date_prefix)
    curr_group_label = tk.Label(win, text=curr_group_prefix)
    curr_comment_label = tk.Label(win, text=curr_comment_prefix)

    # arrange label widgets
    people_label.grid(column=3, row=1, sticky=tk.E)
    location_label.grid(column=3, row=2, sticky=tk.E)
    date_label.grid(column=3, row=3, sticky=tk.E)
    group_label.grid(column=3, row=4, sticky=tk.E)
    comment_label.grid(column=3, row=5, sticky=tk.E)
    # -- display current photo metadata
    curr_people_label.grid(column=1, row=12, sticky=tk.W)
    curr_location_label.grid(column=1, row=13, sticky=tk.W)
    curr_date_label.grid(column=1, row=14, sticky=tk.W)
    curr_group_label.grid(column=1, row=15, sticky=tk.W)
    curr_comment_label.grid(column=1, row=16, sticky=tk.W)

    # create string vars for live text input
    people_sv = tk.StringVar()
    location_sv = tk.StringVar()
    date_sv = tk.StringVar()
    group_sv = tk.StringVar()
    comment_sv = tk.StringVar()

    # add string var tracing so we can get live input
    people_sv.trace("w", lambda name, index, mode, sv=people_sv: write_input(sv, "people"))
    location_sv.trace("w", lambda name, index, mode, sv=location_sv: write_input(sv, "location"))
    date_sv.trace("w", lambda name, index, mode, sv=date_sv: write_input(sv, "date"))
    group_sv.trace("w", lambda name, index, mode, sv=group_sv: write_input(sv, "group"))
    comment_sv.trace("w", lambda name, index, mode, sv=comment_sv: write_input(sv, "comment"))

    # create entry widgets (text input fields)
    people_entry = tk.Entry(win, textvariable=people_sv, bd=5)
    location_entry = tk.Entry(win, textvariable=location_sv, bd=5)
    date_entry = tk.Entry(win, textvariable=date_sv, bd=5)
    group_entry = tk.Entry(win, textvariable=group_sv, bd=5)
    comment_entry = tk.Entry(win, textvariable=comment_sv, bd=5)

    # arrange entry widgets
    people_entry.grid(column=4, row=1)
    location_entry.grid(column=4, row=2)
    date_entry.grid(column=4, row=3)
    group_entry.grid(column=4, row=4)
    comment_entry.grid(column=4, row=5)

    # create buttons
    button_exit = tk.Button(win, text="Quit Application", command=win.quit)
    button_prev = tk.Button(text='Previous image', command=prev_img)
    button_next = tk.Button(text='Next image', command=next_img)
    # button_save = tk.Button(text="Save image", command=save_img)

    # arrange buttons
    button_exit.grid(column=4, row=0)
    button_prev.grid(column=0, row=12)
    button_next.grid(column=2, row=12)
    # button_save.grid(row=win.grid_size()[1], column=win.grid_size()[0] - 1)

    # show the first image
    next_img()


def display_search():
    global filter_people_entry, filter_location_entry, filter_date_entry, \
        filter_group_entry, filter_comment_entry, filterbox_lb

    # create label widgets
    filter_people_label = tk.Label(win, text="Filter by People: ")
    filter_location_label = tk.Label(win, text="Filter by Location: ")
    filter_date_label = tk.Label(win, text="Filter by Date: ")
    filter_group_label = tk.Label(win, text="Filter by Group: ")
    filter_comment_label = tk.Label(win, text="Filter by Comment: ")

    # arrange label widgets
    filter_people_label.grid(column=3, row=8, sticky=tk.E)
    filter_location_label.grid(column=3, row=9, sticky=tk.E)
    filter_date_label.grid(column=3, row=10, sticky=tk.E)
    filter_group_label.grid(column=3, row=11, sticky=tk.E)
    filter_comment_label.grid(column=3, row=12, sticky=tk.E)

    # create string vars for live input
    filter_people_sv = tk.StringVar()
    filter_location_sv = tk.StringVar()
    filter_date_sv = tk.StringVar()
    filter_group_sv = tk.StringVar()
    filter_comment_sv = tk.StringVar()

    # add string var tracing so we can get live input
    filter_people_sv.trace("w", lambda name, index, mode, sv=filter_people_sv: filter_images(sv, "people"))
    filter_location_sv.trace("w", lambda name, index, mode, sv=filter_location_sv: filter_images(sv, "location"))
    filter_date_sv.trace("w", lambda name, index, mode, sv=filter_date_sv: filter_images(sv, "date"))
    filter_group_sv.trace("w", lambda name, index, mode, sv=filter_group_sv: filter_images(sv, "group"))
    filter_comment_sv.trace("w", lambda name, index, mode, sv=filter_comment_sv: filter_images(sv, "comment"))

    # create entry widgets (text input fields)
    filter_people_entry = tk.Entry(win, textvariable=filter_people_sv, bd=5)
    filter_location_entry = tk.Entry(win, textvariable=filter_location_sv, bd=5)
    filter_date_entry = tk.Entry(win, textvariable=filter_date_sv, bd=5)
    filter_group_entry = tk.Entry(win, textvariable=filter_group_sv, bd=5)
    filter_comment_entry = tk.Entry(win, textvariable=filter_comment_sv, bd=5)

    # arrange entry widgets
    filter_people_entry.grid(column=4, row=8)
    filter_location_entry.grid(column=4, row=9)
    filter_date_entry.grid(column=4, row=10)
    filter_group_entry.grid(column=4, row=11)
    filter_comment_entry.grid(column=4, row=12)

    # create listbox widget
    filterbox_lb = tk.Listbox(win, height=10, width=25, bg="grey", activestyle='dotbox', font="Helvetica", fg="yellow")

    # arrange search components
    filterbox_lb.grid(column=4, row=13, columnspan=2, rowspan=4, pady=2)

    # create buttons
    button_export = tk.Button(win, text="Export Filtered Results", command=export_images)

    # arrange buttons
    button_export.grid(column=4, row=18)

    filter_images("", None)


def is_image_file(filename: str):
    # at minimum, must be ".jpg" (4) or larger like ".jpeg" (5)
    if not len(filename) > 4:
        return False
    is_jpg = filename[-3:].lower() == 'jpg' or filename[-4:].lower() == 'jpeg'

    return is_jpg


def pick_path():
    """
    Prompt user to select directory where photos are located
    :return: bool indicating if path is valid
    """
    global images

    home = str(Path.home())
    selected_path = filedialog.askdirectory(initialdir=home)
    if not len(selected_path) > 0:
        return False
    else:
        os.chdir(selected_path)

        files = []
        for (dirpath, dirnames, filenames) in walk(selected_path):
            files.extend(filenames)

        images = []
        for filename in files:
            if is_image_file(filename):
                images.append(filename)

        button_pick_path.destroy()

        asyncio.run(index_images())

        display_search()
        display_editor()


button_pick_path = tk.Button(text='Click to select image folder', command=pick_path)
button_pick_path.grid(column=win.grid_size()[1], row=win.grid_size()[0])

win.mainloop()
