# ACR122U NFC/RFID Reader Monitor

A small desktop application for checking an **ACR122U USB NFC/RFID reader** and viewing information from compatible contactless cards or tags.

The software provides a live display of whether a reader is connected, whether a card is present, and the card identifier returned by the reader. It is intended for basic reader testing, tag identification, and troubleshooting.

## Main features

| Feature | What it does |
| --- | --- |
| Reader connection | Shows whether a compatible reader is detected and displays its name. |
| Card detection | Indicates whether a card or tag is currently present. |
| Card identification | Displays the card's unique identifier (UID) in hexadecimal and decimal formats, when supported. |
| Card details | Displays the card's ATR (Answer to Reset), information reported when the card connection is established. |
| Last-seen time | Shows when a card was most recently read successfully. |
| Event log | Records reader connection changes and newly detected card identifiers during the current session. |
| Error messages | Displays reader, connection, and card-reading errors. |

The window also provides **Clear Log** and **Quit** buttons.

## How it works

1. Connect the ACR122U reader to the computer by USB.
2. Start the application. It checks for available PC/SC-compatible readers and uses the first one found.
3. Place a compatible contactless card or tag on the reader.
4. The application displays the card's ATR and attempts to retrieve its UID.
5. When a new UID is detected, the event log adds an entry with the card information and time.
6. Remove or replace the card to continue testing. The application checks reader and card status approximately four times per second.

The information is displayed locally on the computer. The event log is held in the application's window and is not saved automatically to a file or database.

## Requirements

- A computer with Python 3 and a graphical desktop environment.
- An **ACR122U** USB NFC/RFID reader, or a compatible PC/SC reader supporting the UID command used by this application.
- The reader's appropriate drivers and PC/SC service installed and working on the computer.
- Python's **Tkinter** graphical interface library.
- The **pyscard** Python package.

Card compatibility depends on the reader and card type. Some cards may be detected even when their UID cannot be retrieved.

## Installation and use

1. Download the project and extract the files.
2. Connect the reader and ensure the operating system recognizes it.
3. Open a terminal in the project folder and install the Python dependency:

   ```bash
   python -m pip install pyscard
   ```

4. Start the application:

   ```bash
   python RFID_ACR122U.py
   ```

   On systems where Python 3 is invoked as `python3`, use that command instead of `python`.

5. Present a compatible card or tag to the reader and observe the displayed information.

If the application shows **NOT CONNECTED**, check the USB connection, reader driver, and PC/SC service. If a card is present but the UID cannot be read, the card type or reader may not support the requested UID command.

## Project files

The supplied project contains one Python script:

`RFID_ACR122U.py` — the complete desktop interface, reader monitoring, card-reading logic, and session log.

## Scope and limitations

- The application monitors **one reader at a time**: the first reader reported by the system.
- It reads identification information but does **not** write data to cards.
- It does **not** provide access control, user registration, or card authorization.
- It does **not** export results or send them to another system.
- It uses a PC/SC connection and does **not** read or produce raw Wiegand signals.
- A card UID alone should not be treated as secure proof of identity.
