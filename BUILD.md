# Building Accordion Tuning Lab 3.4

These instructions are for developers only. Users can download the ready-made installer from [Releases](https://github.com/Zwadke/Accordion-Tuning-Lab/releases/latest).


Use Python 3.12 with Tkinter. From the repository directory on Windows:

```bat
py -3.12 -m pip install -r requirements.txt
py -3.12 Accordion_Tuning_Lab.py
```

To build the standalone executable and installer, install [Inno Setup 6](https://jrsoftware.org/isdl.php) and run `Build.bat`. The executable appears in `dist/` and the installer in `Output/`.

## Build and test on Windows

Extract or clone the entire repository. Python 3.12 must be available through `py -3.12`. Install Inno Setup 6 in its default location. Run `Build.bat` with an internet connection; it creates a virtual environment and installs the build dependencies.

Test `dist/Accordion_Tuning_Lab.exe` and `Output/Accordion_Tuning_Lab_Setup.exe` on Windows, including audio, MIDI and language switching. The installer is per-user and unsigned. Review [third-party license notes](docs/Third-party.md) before distributing a build.
