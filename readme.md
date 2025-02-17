# Magic Extractor


## Description
Magic Extractor is a universal extraction tool designed to handle multiple compressed file formats. It utilizes a combination of detection techniques to accurately identify and extract contents from compressed files, supporting a wide range of formats.

## Development Status
Although the Magic Extractor is fully functional, it is still under active development and not yet finalized for a release version. Consequently, the repository does not have any release tags yet, and features or functionality may change as the project evolves.

## Project Structure
The project is organized into several main folders:
- `src`: Contains the source code of the project.
  - `bin`: Includes binary files and detectors for various file types.
  - `formats`: Contains Python modules for handling specific file formats.
- `test`: Houses test files and scripts for various compression formats.

## Features
- Supports multiple compression formats including 7z, RAR, ALZip, and more.
- Utilizes MIME type detection and specific binary detections to handle files.
- Offers a configurable setup through command-line arguments for tailored usage.

## Installation
To set up the Magic Extractor, clone the repository and install the required Python packages:
```bash
git clone https://github.com/yourusername/magic-extractor.git
cd magic-extractor
pip install -r src/requirements.txt
```

## Usage
To use Magic Extractor, run the `main.py` script with the necessary arguments:
```bash
python src/main.py <path_to_file> <output_directory> [options]
```
Options include:
- `--password <password>`: Specify a password for encrypted files.
- `--debug`: Enable detailed log output for debugging.
- Additional flags for customization:
  - `--open-output-folder <bool>`: Open output folder after extraction.
  - `--check-free-space <bool>`: Check disk space before extraction.
  - `--extract-video-tracks <bool>`: Extract video tracks if available.
  - `--warn-before-executing <bool>`: Warn before executing any executable file.
  - `--check-unicode <bool>`: Check for unicode characters in file names.
  - `--fix-file-extensions <bool>`: Automatically fix file extensions.
  - `--create-log-files <bool>`: Create log files of the operations.
  - `--fast-check`: Perform a fast type check by reading only the first 2048 bytes.
  - `--no-fast-check`: Disable fast type check.

## Supported Formats
A complete list of all supported file formats can be found in the `formats.md` file included in the project repository.

## Contributing
Contributions to Magic Extractor are welcome! Please read the contributing guidelines in `CONTRIBUTING.md` (to be created) before submitting pull requests.

## License
This project is licensed under the LGPL-3.0-only - see the `LICENSE.txt` file for details.

## Authors and Acknowledgment
- Lead Developer: DSR! - xchwarze@gmail.com
- Thanks to all contributors who have helped to enhance this project.

## Support
If you find this project useful, consider supporting it by providing feedback, contributing code, or donations.
