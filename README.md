# bscripts: Automated Type-Beat Processing Pipeline

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?logo=python&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Processing-007808.svg?logo=ffmpeg&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57.svg?logo=sqlite&logoColor=white)
![Dropbox](https://img.shields.io/badge/Dropbox-Cloud%20Sync-0061FF.svg?logo=dropbox&logoColor=white)

A comprehensive Python-based pipeline that fully automates the processing, cloud-syncing, and bulk-scheduling of type-beats and music loops.

# The Problem
Consistently uploading type-beats to YouTube and beat stores is a highly repetitive and tedious process. For every single beat, a producer has to render a looping video, compress stems into a `.zip` archive, generate an MP3 and WAV master, design thumbnails, and manually type out YouTube descriptions with the correct BPM, Key, and purchase links. When trying to maintain a daily upload schedule, this administrative overhead takes hours away from actual music production and quickly leads to burnout. 

# The Solution
**bscripts** is a suite of Python tools designed to fully automate the post-production and publishing pipeline for music producers. By standardizing the file naming convention from the DAW, these scripts handle file compression, video rendering, subtitle generation, and database management. Finally, the system automatically offloads the heavy video files to Dropbox and generates a `.csv` file perfectly formatted for bulk-scheduling via SocialChamp. This turns hours of daily upload management into a fast, bulk-processed workflow that takes only minutes.

# The Pipeline
The workflow is divided into 5 distinct steps, minimizing manual input:

### 1. DAW Export
The producer exports the raw `.wav` stems directly from their DAW into a designated folder. The folder/file must follow a specific naming convention to allow the scripts to parse the metadata (e.g., `Producer 1 x Producer 2 - Beat Title 140 Cmin_Master.wav`).

### 2. Processing (`typebeat.py`)
This script acts as the core processing engine. It sweeps the exported folders and automatically:
- Isolates the `master.wav` file for the beat store.
- Compresses the remaining stems into a `stems.zip` archive using `7z`.
- Renders an MP3 version.
- Generates a looping `video.mp4` using a randomly selected background video and picture from your designated assets folder.
- Parses the filename via regex to extract the Name, Collaborators, Key, and Tempo, saving this data into a local SQLite database (`beats.db`).

### 3. Store Upload & Link Management (`beat_management.py`)
With the audio files prepped and zipped, the producer manually uploads the `master.wav` and `stems.zip` to their beat store (e.g., BeatStars, Airbit). Once uploaded, the producer retrieves the purchase links. By running the interactive `add_links` command in `beat_management.py`, the system quickly prompts the user to paste the purchase links for any beats missing them in the database. This is heavily optimized for fast bulk-entry.

### 4. YouTube Prep & Cloud Sync (`yt_new.py`)
Once the database has the purchase links, this script prepares the final social media assets. For each video, it:
- Looks up the beat's metadata in the database.
- Generates a rotating `.srt` subtitle file that periodically displays the beat title, Key/BPM, and a bulk sale message (e.g., "Buy 2 Get 2 Free").
- Automatically uploads the video, thumbnail, and subtitles to Dropbox via their API.
- Generates a rich YouTube description containing the purchase link, social links, and targeted tags.
- Compiles all of this into a single `.csv` file formatted for bulk uploading.

### 5. Automated Scheduling
The producer takes the generated `.csv` and uploads it to SocialChamp (or a similar bulk-scheduling tool). The scheduler automatically pulls the heavy video files and thumbnails directly from the Dropbox links generated in Step 4. The upload schedule is handled entirely in the cloud, making the final step practically instantaneous on the user's end.

# Installation
It is required to have Python 3.10+ installed. A virtual environment is recommended.
1. Install the required Python packages (e.g., `dropbox`, `srt`).
2. **System Dependencies:** This suite heavily relies on external command-line tools. You must have `ffmpeg` and `7z` (7-Zip) installed and accessible in your system's PATH. 
3. Rename `config.defaults.json` to `config.json` and fill in your specific paths (video/picture asset directories, export directories, social links).
4. Export your Dropbox API token to your environment variables (`export DROPBOX_TOKEN="your_token_here"`).

# Usage
Everything is executed via the command line.

- **To process new exports:** 
  Run `python typebeat.py`. The script will prompt you to select an artist profile and provide the root directory of your recent DAW exports.
- **To manage the database and add links:** 
  Run `python beat_management.py`. Type `b` (for beats), and then use commands like `list`, `search`, or `add_links` to interactively update your catalog.
- **To generate the upload CSV:** 
  Run `python yt_new.py`. Provide the channel name and the directory containing the finished `.mp4` files.

## Naming convention
The script is based on a strict naming convention to parse data and save it to a database. Not following it will result in crashes or incorrect data.

### Beats
Beats must be named using the following structure:
`[Producer(s)] - [Beat Name] [BPM] [Key].wav`

**Rules:**
- There **must** be a space before and after the hyphen (` - `) separating the producers from the beat name.
- Producers can be separated by ` x ` and can include the `@` symbol (the script will clean these up automatically).
- The Beat Name, BPM, and Key **must** be separated by spaces.
- There **must** be an underscore (`_`) connecting the Key to the file suffix (e.g., `_Master.wav`). This is done in FL Studio automatically and one does not have to change anything as long as the naming convention above is followed. 

**Examples:**
- `prodname - beat name 140 Cmin` *(Solo)*
- `prodname x coprod - beat name 122 F#min` *(Collab)*

### Loops
Loops use a slightly different structure and are parsed from right to left:
**`[Loop Name] [BPM] [Key] x[Collaborator(s)].wav`**

# Other notes:
- **Channel Configs:** You can manage multiple YouTube channels by adding specific `.json` files to the `channel_configs/` directory, allowing for dynamic YouTube tags, titles, and descriptions depending on the brand.
