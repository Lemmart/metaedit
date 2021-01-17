## Project Overview
**Problem:** Amateur archivists, parents looking to record family history, and other hobbyists do not have a simple way to save key information about images into older digital photos. This tool will help the next generation provide answers about the events and people before them and aims to improve the transfer of information from one generation to the next.

**Questions that good metadata can solve:**
1. Who are all these people in this old photo?
1. What was happening in this photo?
1. Where was this photo taken?
1. Where did this take place?
1. Why is everyone crowding around the person in the middle?

**Solution:** `MetaEdit`, a simple image viewer and editor, was conceived to solve this problem. It edits the metadata of an image directly, but does not modify the image itself. This preserves image quality while updating the `ImageDescription` key in the photo exif data. This ensures that as the photo is transferred among users or across platforms (make sure you aren't using something like FaceBook which will strip out metadata!), the detailed information cataloging who, what, when, where, and why is not lost for future audiences. 

## Compatibility
- **Supported Image Files:** JPEG, JPG, jpeg, and jpg image files. No support for HEIC (most recent iPhone image format).
- **OS:** Windows 10, MacOS

## How to download?
- **Windows 10:** download the `metaedit.exe` file in `dist/metadata.app/Windows10/`
- **MacOS:** download the `metaedit` file in `dist/metadata.app/MacOS/`

## Contributing
Please submit pull requests from a personal branch against the `main` repository branch. Pull requests will be reviewed in a timely fashion and may be merged upon approval only.

## Building a MacOS executable on MacOS
- Install `pyinstaller` which will package up the python script: `pip install pyinstaller`
- Navigate to the project: `cd ~/myproject`
- Package the project: `pyinstaller —windowed —noconsole —onefile mypythonscript.py`
- Check out the dist/ directory
- Distribute the `mypythonscript` executable

## Building a Windows 10 executable on MacOS
- Set up virtual box
    - Download Virtual Box from https://www.virtualbox.org/wiki/Downloads 
    - Download a Windows ISO file (basically the OS) from https://www.microsoft.com/en-us/software-download/windows10ISO 
- Configure Virtual Box
    - Use Microsoft Windows10 (64-bit to match the downloaded Windows ISO file)
    - Provide at least 4096 MB (4GB) of RAM
    - Provide at least 25 GB of dynamically (or fixed) storage space on a virtual disk image (vdi)
    - Navigate to Settings > Storage > Storage Devices and click the second subheading under “Controller: SATA” —> then click the blue disk icon and select the Windows 10 ISO
        - This should consume about 5-6 GB
    - Should end up with something like the below image
- Boot up the virtual machine and install windows
    - Be sure to select that you do not have a product key (Microsoft will still let you use windows basically normally)
- In the machine:
    - Navigate to https://www.python.org/downloads/windows/ and select the latest Python 3 release
    - Download the recommended Windows installer (64-bit) from the options in the box
    - Follow the installer steps and be sure to select `Add python to PATH` (will save a lot of pathing headaches later)
    - Open `Powershell` (Microsoft’s linux-like CLI)
    - Install pyinstaller which will package up our python script: `pip install pyinstaller`
- In Powershell:
    - Navigate to the project: `cd $HOME/myproject`
    - Package the project: `pyinstaller —windowed —noconsole -F mypythonscript.py`
    - Check out the dist/ directory
    - Distribute the `mypythonscript.exe` executable!
