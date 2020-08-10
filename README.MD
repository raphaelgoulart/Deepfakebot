# Deepfakebot

A Discord bot that invokes A. Siraohin's [First Order Motion Model for Image Animation](https://github.com/AliaksandrSiarohin/first-order-model/) with user-supplied input.

### Quick disclaimer

I'm not a Python expert (I've learned most of this while coding the bot itself), this was made mostly for personal use but I'm sharing this because it might be useful for other people. If you have any questions or issues, contact ```goulart#3978``` at Discord.

Also, if you host this on your own computer, be aware that the deepfake creation process (independent from the bot) is resource-intensive and will probably slow down your computer (or worse) while it is being done.

## Requirements

This was made using Python 3.6.9.

This bot does not include [the animation program itself](https://github.com/AliaksandrSiarohin/first-order-model/), so you'll need to get it up and running — if you're able to run ```demo.py``` and ```crop-video.py```, you're good to go.

You'll also need the face-alignment library, and the pre-trained checkpoint ```vox-cpk.pth.tar```, which should be saved on the root of the animation program folder (both are also available on the link above).

Afterwards, just run ```pip install -r requirements.txt``` to install the requirements for the bot itself.

If the ```crop-video.py``` script of the animation program throws an error on some videos where it's expected to work, run ```pip install --upgrade imageio``` and ```pip install imageio-ffmpeg``` to fix that.
(Replace ```pip``` for ```pip3``` on the commands if needed)

A NVIDIA GPU is not required, but massively recommended; it's possible to run the animation program on the CPU, however that is massively slow and not recommended at all.

## Deployment instructions

- Create a bot account on [Discord's  Developer Portal](https://discord.com/developers/applications);
- Get [the animation program](https://github.com/AliaksandrSiarohin/first-order-model/) up and running;
- On ```deepfakebot.py```, edit ```path_to_exe = 'path/to/first-order-model-master/'``` (line 20) to the directory where the animation program is located in your system;
- Edit the last line (```bot.run('token')```), replacing ```token``` with your bot's token;
- Create a ```data``` folder on the folder where the bot is located, and a ```temp``` folder inside of the ```data``` folder;
  - Alternatively, edit the ```path_to_temp``` variable (line 21) for the location where you want the bot to store its temporary files;
- If needed, replace all ```python3``` references in the code to your Python 3 executable location;
- Last but not least, run the bot with the ```python deepfakebot.py``` command.

### Running on CPU (NOT RECOMMENDED!)

If you want to run the animation program on your CPU rather than on the GPU, edit both ```create_subprocess_exec``` calls to add the ```--cpu``` parameter to the scripts being called.

## Usage instructions

- ```>deepfake link_to_image* link_to_video [--silent] [--dont_crop_image] [--dont_crop_video] [--smart_crop] [--find_best_frame] [--absolute]```
  - ```*link_to_image``` can be a URL or an attachment;
  - Parameters enclosed in brackets are optional;
  - ```--silent``` hides details about the progress of the deepfake creation;
  - ```--dont_crop_image``` adds black bars to non-square images instead of cropping them;
  - ```--dont_crop_video``` adds black bars to non-square videos instead of cropping them;
  - ```--smart_crop``` enables the usage of ```crop-video.py``` (instead of just center-cropping it)(ignored if ```--dont_crop_video``` is set);
  - ```--find_best_frame``` makes the alignment start from the frame that is the most aligned with the source image;
  - ```--absolute``` aligns the face using absolute coordinates, instead of relative (it is useless to use ```--find_best_frame``` together with this option).
  - ```--smart_crop``` and ```--find_best_frame``` tend to increase the execution time a lot; use with caution.
- ```>deepfake``` (no arguments): Shows usage instructions for the bot;
- ```>help```: Shows discord.py's default help message;
- ```>adv_help```: Shows advanced instructions to help users yield better results.

## TO DO

- Import the animation program as a submodule, instead of using ```create_subprocess_exec```;
- Make the bot edit the message to show the current percentage / remaining time for the deepfake creation process;
- Same as above, but for the ```crop-video.py``` script;
- Cleaning, optimization, etc etc.