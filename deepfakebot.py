from __future__ import unicode_literals
import discord
from discord.ext import commands
import PIL
from PIL import Image
from io import BytesIO
import requests
import youtube_dl
import random
import string
import ffmpeg
import os
import subprocess
import asyncio

prefix='>'
description = '''Bot that automates the creation of deepfakes, using the First Order Motion Model for Image Animation algorithm by Aliaksandr Siarohin et al.'''
bot = commands.Bot(command_prefix=prefix, description=description)

path_to_exe = 'path/to/first-order-model-master/'
path_to_temp = 'data/temp/'
image_format = '.png'
video_format = '.mp4'

help = '''The command should be run as follows:

`''' + prefix + '''deepfake link_to_image* link_to_video [--silent] [--dont_crop_image] [--dont_crop_video] [--smart_crop] [--find_best_frame] [--absolute]`

\\*`link_to_image` can be a URL or an attachment;
Parameters enclosed in brackets are optional;
`--silent` hides details about the progress of the deepfake creation;
`--dont_crop_image` adds black bars to non-square images instead of cropping them;
`--dont_crop_video` adds black bars to non-square videos instead of cropping them;
`--smart_crop` enables the usage of `crop-video.py` (instead of just center-cropping it)(ignored if `--dont_crop_video` is set);
`--find_best_frame` makes the alignment start from the frame that is the most aligned with the source image;
`--absolute` aligns the face using absolute coordinates, instead of relative (it is useless to use `--find_best_frame` together with this option).
`--smart_crop` and `--find_best_frame` tend to increase the execution time a lot; use with caution.

Based on "First Order Motion Model for Image Animation" by Aliaksandr Siarohin et al.: <https://github.com/AliaksandrSiarohin/first-order-model>'''

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command()
async def deepfake(ctx, *args):
    """Creates a deepfake; run this without arguments to show instructions"""
    if(len(args)==0): await ctx.send(help)
    else:
        try:
            image, video, silent, dont_crop_image, smart_crop, dont_crop_video, find_best_frame, absolute = parseArgs(ctx.message, args)
            try:
                message = None
                random_string = get_random_string(10)
                if(not silent): 
                    text = 'Downloading driving video and source image...'
                    if(absolute and find_best_frame): text = '**Warning: ** `--find_best_frame` is not needed if `--absolute` is used!\n' + text
                    if(smart_crop and dont_crop_video): text = '**Warning: ** `--smart_crop` is ignored if `--dont_crop_video` is set!\n' + text
                    message = await ctx.send(text)
                if(dont_crop_image): image = add_black_border(image)
                else: image = crop_center(image)
                image.save(path_to_temp + random_string + image_format)
                video_download_succeeded = True
                try:
                    with youtube_dl.YoutubeDL({'outtmpl': path_to_temp + random_string + '.%(ext)s', 'forcefilename': 'True', 'merge_output_format': 'mkv'}) as ydl:
                        info = ydl.extract_info(video, download=True)
                        video = ydl.prepare_filename(info)
                        print(video)
                except Exception as e:
                    error = 'Error downloading video; check if the provided url is a valid video.'
                    if(silent): await ctx.send(error)
                    else: await message.edit(content = message.content + '\n' + error)
                    video_download_succeeded = False
                    os.remove(path_to_temp + random_string + image_format)
                if(video_download_succeeded):
                    filename = path_to_temp + random_string + '.crop' + video_format
                    video_data = ffmpeg.probe(video)['streams'][0]
                    print(video_data)
                    if(dont_crop_video and video_data['width'] != video_data['height']):
                        stream = ffmpeg.input(video) # this might fail if youtube-dl format output is different than what ydl.prepare_filename(info) gets
                        filename = path_to_temp + random_string + '.out' + video_format
                        #add black bars
                        square = max(video_data['width'], video_data['height'])
                        (stream
                        .filter_('scale', w=square, h=square, force_original_aspect_ratio='decrease')
                        .filter_('pad', w=square, h=square, x='(ow-iw)/2', y='(oh-ih)/2')
                        .filter_('setsar', '1'))
                        stream.output(filename).run()
                        os.remove(video)
                        video = filename
                    elif(not dont_crop_video):
                        smart_crop_success = True
                        if(smart_crop):
                            if(not silent): await message.edit(content = message.content + '\n' + "Attempting to run `crop-video.py`...")
                            try: #crop_video.py
                                # process = subprocess.run(["python3", path_to_exe + 'crop-video.py', '--inp', video], check=True, stdout=subprocess.PIPE, universal_newlines=True)
                                proc = await asyncio.create_subprocess_exec("python3",
                                    path_to_exe + 'crop-video.py', '--inp', video,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=None)
                                output, stderr = await proc.communicate()
                                print(output)
                                dimensions = [s for s in output.decode("utf-8").split() if "crop=" in s]
                                if (len(dimensions) == 0): 
                                    smart_crop_success = False
                                    if(not silent): await message.edit(content = message.content + '\n' + "crop-video.py didn't return any results (possibly wasn't able to detect a face on the video for long enough)")
                                else:
                                    if (len(dimensions) > 1 and not silent): await message.edit(content = message.content + '\n' + "crop-video.py returned more than one set of coordinates (video might look glitchy)")
                                    dimensions = dimensions[0].split(':')
                                    dimensions[0] = dimensions[0][6:]
                                    dimensions[3] = dimensions[3][0:-1]
                                    print(dimensions)
                                    stream = ffmpeg.input(video)
                                    (stream
                                    .filter_('crop',w=dimensions[0], h=dimensions[1], x=dimensions[2], y=dimensions[3])
                                    .filter_('scale', w=256, h=256))
                                    stream.output(filename).run()
                                    os.remove(video)
                                    video = filename
                            except Exception as e:
                                print(e)
                                if(not silent): await message.edit(content = message.content + '\n' + "An error has occurred on crop-video.py; check the log for details")
                                smart_crop_success = False
                        if((not smart_crop_success or not smart_crop) and video_data['width'] != video_data['height']): # manually crop video if crop_video.py fails
                            if(not silent): await message.edit(content = message.content + '\n' + "Cropping video manually...")
                            square = min(video_data['width'], video_data['height'])
                            stream = ffmpeg.input(video)
                            stream.filter_('crop',w=square, h=square, x=video_data['width'] - square // 2, y=video_data['height'] - square // 2)
                            stream.output(filename).run()
                            os.remove(video)
                            video = filename
                    if(not silent): await message.edit(content = message.content + '\n' + "Creating deepfake... (this might take a while)")
                    result_filename = path_to_temp + random_string + '.result' + video_format
                    #command = ["python3", path_to_exe + 'demo.py', '--config', path_to_exe + 'config/vox-256.yaml', '--driving_video', video, '--source_image', path_to_temp + random_string + image_format, 
                    #'--checkpoint', path_to_exe + 'vox-cpk.pth.tar', '--result_video', result_filename, '--adapt_scale']
                    command = [path_to_exe + 'demo.py', '--config', path_to_exe + 'config/vox-256.yaml', '--driving_video', video, '--source_image', path_to_temp + random_string + image_format, 
                    '--checkpoint', path_to_exe + 'vox-cpk.pth.tar', '--result_video', result_filename, '--adapt_scale']
                    if(not absolute): command.append('--relative')
                    if(find_best_frame): command.append('--find_best_frame')
                    #subprocess.run(command)
                    proc = await asyncio.create_subprocess_exec("python3", *command)
                    await proc.communicate()
                    os.remove(path_to_temp + random_string + image_format)
                    input_video = ffmpeg.input(result_filename)
                    input_audio = ffmpeg.input(video)
                    filename = path_to_temp + random_string + '.output' + video_format
                    ffmpeg.concat(input_video, input_audio, v=1, a=1).output(filename).run()
                    os.remove(result_filename)
                    os.remove(video)
                    try:
                        await ctx.send(file=discord.File(filename))
                        os.remove(filename)
                    except Exception as e:
                        await ctx.send("An error has occurred while uploading the deepfake! (Connection error, or result file too large)")
                        os.remove(filename)
            except Exception as e:
                print(e)
                await ctx.send("An error has occurred! Check the log for details")
        except Exception as e:
            await ctx.send(e)

def parseArgs(message, args):
    current_arg = 0
    image = None
    if(len(message.attachments)>1): 
        raise Exception("Only one image should be sent as an attachment.")
    elif(len(message.attachments)==1):
        try:
            image = Image.open(BytesIO(requests.get(message.attachments[0].url).content))
            image.load()
        except Exception as e: 
            print(e)
            raise Exception("An error has occurred; Make sure your attachment is a valid image.")
    else:
        try:
            image = Image.open(BytesIO(requests.get(args[0].strip('<>')).content))
            image.load()
            current_arg = 1
        except Exception as e: 
            print(e)
            raise Exception("An error has occurred; Make sure the first argument is a valid image.")
    if(len(args) < current_arg + 1): 
        if(current_arg == 0): raise Exception("An error has occurred; Make sure the first argument is a valid video.")
        else: raise Exception("An error has occurred; Make sure the second argument is a valid video.")
    video = args[current_arg].strip('<>') # this does not confirm if the video does work
    silent = False
    dont_crop_image = False
    smart_crop = False
    dont_crop_video = False
    find_best_frame = False
    absolute = False
    for arg in args[current_arg+1:]:
        if(arg=='--silent'): silent = True
        elif(arg=='--dont_crop_image'): dont_crop_image = True
        elif(arg=='--smart_crop'): smart_crop = True
        elif(arg=='--dont_crop_video'): dont_crop_video = True
        elif(arg=='--find_best_frame'): find_best_frame = True
        elif(arg=='--absolute'): absolute = True
    return image, video, silent, dont_crop_image, smart_crop, dont_crop_video, find_best_frame, absolute

def get_random_string(length):
    letters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def add_black_border(im, fill_color=(0, 0, 0, 0)):
    x, y = im.size
    size = max(x, y)
    new_im = Image.new('RGBA', (size, size), fill_color)
    new_im.paste(im, (int((size - x) / 2), int((size - y) / 2)))
    return new_im

def crop_center(pil_img):
    img_width, img_height = pil_img.size
    crop_width = min(pil_img.size)
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_width) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_width) // 2))

@bot.command()
async def adv_help(ctx):
    """Shows advanced instructions to help users yield better results"""
    await ctx.send("""**Advanced usage instructions**
These may help you yield better results, if your current ones aren't satisfying.

**Source image**

```
* Must show the person's whole face (or most of it at least), preferably from a front perspective;
* The face must be zoomed in and centered on the image;
* The image must be a square -- if it isn't, the algorithm will center-crop the image, making it square;
* If your image is a non-square picture, but cropping it results in important data loss (e.g. a vertical photo of one's face), you can add the `--dont_crop_image` parameter to make the bot add a black border to make the image square, instead of cropping it.```
**Driving video**

The same guidelines for the source image also apply here; the video must be a square, with the person's whole face being centered and shown fully for as long as possible.
Sadly, that's not as easy to achieve as simply cropping an image (depending on the video, it's not possible at all). However, a couple techniques can help:
```
* Trimming the video to remove unwanted segments (leaving only the person's face);
* Stabilizing the footage, in order to keep the face centered (to a reasonable extent);
* Then, cropping the video so it is a square centered on the person's face.```
The third step can be done by the bot in the following ways:
```
* By default, it will center-crop the video if it's not a square already;
* If the --dont_crop_video parameter is used, it will add black bars to make the video square, instead of cropping it;
* If the --smart_crop parameter is used, it will run crop-video.py, an AI-based algorithm to determine the best coordinates to crop the video. However, it has a long execution time and doesn't always work.```""")
    await ctx.send("""**Common problems (and their solutions)**

```
* Source image is square, but the face isn't zoomed or centered
Solution: just crop it in any image editing program - it doesn't really matter if the resolution is low, as long as the face is zoomed and centered.

* Black frame on the start of driving video / video doesn't start with the person's face, leading to glitchy results
Solution: just trim it away!

* I don't want to edit the video externally!
Solution: you can still yield decent results with the --find_best_frame or --absolute parameters.
The algorithm's default behavior is to keep the source image's original pose on the first frame of the video, and adjust it accordingly on the following frames.
--find_best_frame will find the frame where the video is the most aligned with the image, and use that as reference. However, it takes longer to execute, and doesn't always work.
--absolute will simply map the exact coordinates from the driving video to the source image, instead of making the changes relative. Sometimes (rarely) it actually looks better!
Neither will be as effective as fixing the driving video, but you might still yield decent and fun results.

* No matter what I do, the video just doesn't look good enough!
Solution: Sadly, some videos just aren't fixable; however, if you have a webcam or a phone camera, you can try reenacting the video you want to use, with the ideal conditions that the program expects. This is a surprisingly common solution in some scenarios.```""")

bot.run('token')