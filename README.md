# Music Deduplication Tool

A powerful, user-friendly application to find and manage duplicate music files across your collection.

![Music Deduplication Tool](https://raw.githubusercontent.com/username/music-dedupe/main/screenshots/app.png)

## Features

- **Smart duplicate detection** using both filenames and ID3 tags
- **Customizable format priorities** to keep your preferred audio formats
- **Drag and drop** support for easy directory selection
- **Multiple matching methods**:
  - Similarity-based matching with adjustable threshold
  - Exact file size matching option for perfect duplicates
  - ID3 tag matching for more accurate results
- **Flexible handling options**:
  - Move duplicates to a separate folder
  - Delete duplicates to free up space
- **Quality awareness**:
  - Automatically keeps the highest quality version of each song
  - Considers format, file size, and bitrate in decisions
- **Cross-platform compatibility**:
  - Works on macOS (including Apple Silicon)
  - Windows support
  - Linux support

## Installation

### Option 1: Download Pre-built Binary

1. Download the latest release for your platform from the [Releases page](https://github.com/username/music-dedupe/releases)
2. macOS: Double-click the `.app` file to launch
3. Windows: Double-click the `.exe` file to launch
4. Linux: Run the executable from the terminal

### Option 2: Run from Source

1. Ensure you have Python 3.6+ installed
2. Clone this repository:
   ```
   git clone https://github.com/username/music-dedupe.git
   cd music-dedupe
   ```
3. Install required dependencies:
   ```
   pip install tkinterdnd2 mutagen
   ```
4. Run the application:
   ```
   python music_dedupe_gui.py
   ```

### Option 3: Build Your Own Executable

1. Ensure you have Python 3.6+ installed
2. Clone this repository:
   ```
   git clone https://github.com/username/music-dedupe.git
   cd music-dedupe
   ```
3. Run the setup script:
   ```
   python setup.py
   ```
4. Find the executable in the `dist` directory

## Usage Guide

### Basic Workflow

1. **Select a source directory** containing your music files
2. **Configure options**:
   - Adjust similarity threshold (higher = stricter matching)
   - Choose to move or delete duplicates
   - Enable/disable ID3 tag support
   - Enable/disable exact size matching if needed
   - Set format priorities to keep your preferred formats
3. **Click "Scan for Duplicates"** to analyze your collection
4. **Review the results** in the log area
5. **Click "Process Duplicates"** to move or delete the duplicates

### Advanced Options

#### Similarity Threshold

- **0.70-0.85**: More aggressive matching, catches more potential duplicates but may include false positives
- **0.85-0.95**: Balanced matching, good for most collections
- **0.95-1.00**: Conservative matching, only very similar files will be considered duplicates

#### Format Priority

Set your preference order for audio formats by assigning higher values (0-10) to formats you prefer to keep:

- Higher value = higher priority
- The app will keep the highest priority file when duplicates are found
- Default priorities: FLAC (4), WAV/AIFF/ALAC (3), M4A (2), MP3 (1), WMA (0)

#### ID3 Tag Support

When enabled, the app will use metadata from your music files to identify duplicates, which is often more accurate than using filenames alone. The app can read tags from:

- MP3 files (ID3 tags)
- FLAC files (Vorbis comments)
- M4A files (iTunes metadata)

#### Exact Size Matching

When enabled, only files with identical sizes will be considered duplicates. This is useful for finding perfect duplicates but will miss files that were encoded differently.

## Configuration

The application saves your settings to `~/.music_dedupe_config.json` so you don't have to set everything up each time you run it.

## Troubleshooting

### Common Issues

- **Application doesn't start**: Ensure you have all required dependencies installed
- **No duplicates found**: Try lowering the similarity threshold
- **Too many duplicates found**: Try increasing the similarity threshold or enabling exact size matching
- **ID3 tags not working**: Install the mutagen library (`pip install mutagen`)
- **Drag and drop not working**: Install the tkinterdnd2 library (`pip install tkinterdnd2`)

### Error Logs

If you encounter issues, check the console output for error messages. Include these when reporting bugs.

## Development

### Building from Source

1. Clone the repository
2. Install development dependencies:
   ```
   pip install tkinterdnd2 mutagen pyinstaller
   ```
3. Run the setup script:
   ```
   python setup.py
   ```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) for drag and drop support
- [mutagen](https://mutagen.readthedocs.io/) for ID3 tag handling
- [PyInstaller](https://www.pyinstaller.org/) for executable creation