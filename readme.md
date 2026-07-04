# Magic Extractor


## Description
Magic Extractor is a universal extraction tool designed to handle multiple compressed file formats. It utilizes a combination of detection techniques to accurately identify and extract contents from compressed files, supporting a wide range of formats.

## Development Status
Although the Magic Extractor is fully functional, it is still under active development and not yet finalized for a release version. Consequently, the repository does not have any release tags yet, and features or functionality may change as the project evolves.

## Project Structure
The project is organized into several main folders:
- `src`: Contains the source code of the project.
  - `bin`: Includes binary files and detectors for various file types.
  - `data`: Runtime configuration. Holds `handlers.json`, the detection/MIME → handler routing map, loaded dynamically so it can be updated without rebuilding.
  - `formats`: Contains Python modules for handling specific file formats.
- `test`: Houses test files and scripts for various compression formats.

## Features
- Supports multiple compression formats including 7z, RAR, ALZip, and more.
- Combines several detection engines (puremagic MIME, Magika, binwalk, DIE, TrID) to identify files.
- Routes detections to extractors through an external, data-driven map (`data/handlers.json`).
- Offers a configurable setup through command-line arguments for tailored usage.

## Installation
To set up the Magic Extractor, clone the repository and install the required Python packages:
```bash
git clone https://github.com/yourusername/magic-extractor.git
cd magic-extractor
pip install -r src/requirements.txt
```

## Usage
Magic Extractor uses subcommands:
```bash
python src/main.py extract  <path_to_file> [output_directory] [options]
python src/main.py identify <path_to_file>   # detect type + candidate handlers, no extraction
python src/main.py list     <path_to_file>   # list archive contents without extracting
python src/main.py carve    <path_to_file> [output_directory]  # carve embedded archives at binwalk offsets and extract them
python src/main.py carve    <path_to_file> --list              # list binwalk fragments (index/offset/size/name)
python src/main.py carve    <path_to_file> --fragment N         # carve a single fragment by index
python src/main.py carve    <path_to_file> --raw                # carve every fragment (binwalk extract-all)
```
`extract` also supports `-r`/`--recursive` (with `--max-depth N`) to extract archives found inside the output.
A bare path with no subcommand defaults to `extract` for backward compatibility:
```bash
python src/main.py <path_to_file> <output_directory> [options]
```
`extract` options include:
- `--password <password>`: Specify a password for encrypted files.
- `--debug`: Enable detailed log output for debugging.
- Additional flags for customization:
  - `--open-output-folder <bool>`: Open output folder after extraction.
  - `--check-free-space <bool>`: Check disk space before extraction.
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
