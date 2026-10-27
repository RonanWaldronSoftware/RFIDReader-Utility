#!/usr/bin/env python3
# pip install pyscard
#
# GUI shows:
# - USB/PCSC reader connected status (and reader name)
# - Live card status (present/absent)
# - ATR + UID (hex + decimal) when a card is tapped
#
# Note: ACR122U is PC/SC NFC; it does not output raw Wiegand pulses.

import time
import tkinter as tk
from tkinter import ttk

from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException

GET_UID = [0xFF, 0xCA, 0x00, 0x00, 0x00]  # ACR122U commonly supports this

POLL_MS = 250  # UI update rate


def hexstr(b: bytes) -> str:
    return b.hex().upper()


def int_be(b: bytes) -> int:
    return int.from_bytes(b, "big", signed=False)


class NFCApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ACR122U NFC Monitor")
        self.root.geometry("820x520")
        self.root.minsize(720, 460)

        # State
        self.last_reader_names = []
        self.last_uid_hex = None
        self.last_seen_ts = None
        self.last_error = ""

        self._build_ui()
        self._poll()

    def _build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Header
        header = ttk.Frame(self.root, padding=(16, 14))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        title = ttk.Label(header, text="ACR122U NFC Monitor", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w")

        self.clock_lbl = ttk.Label(header, text="", font=("Segoe UI", 10))
        self.clock_lbl.grid(row=0, column=1, sticky="e")

        # Main content
        main = ttk.Frame(self.root, padding=(16, 8))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        # Left: Status cards
        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)

        self.reader_card = self._card(left, "Reader Status")
        self.reader_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._build_reader_card(self.reader_card)

        self.card_card = self._card(left, "Card Status")
        self.card_card.grid(row=1, column=0, sticky="ew")
        self._build_card_status_card(self.card_card)

        # Right: Data + Log
        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.data_card = self._card(right, "Card Data")
        self.data_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._build_data_card(self.data_card)

        self.log_card = self._card(right, "Event Log")
        self.log_card.grid(row=1, column=0, sticky="nsew")
        self.log_card.rowconfigure(1, weight=1)
        self.log_card.columnconfigure(0, weight=1)
        self._build_log_card(self.log_card)

        # Footer
        footer = ttk.Frame(self.root, padding=(16, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        self.err_lbl = ttk.Label(footer, text="", foreground="#b00020")
        self.err_lbl.grid(row=0, column=0, sticky="w")

        btns = ttk.Frame(footer)
        btns.grid(row=0, column=1, sticky="e")

        clear_btn = ttk.Button(btns, text="Clear Log", command=self._clear_log)
        clear_btn.grid(row=0, column=0, padx=(0, 8))

        quit_btn = ttk.Button(btns, text="Quit", command=self.root.destroy)
        quit_btn.grid(row=0, column=1)

    def _card(self, parent, title: str):
        frame = ttk.Frame(parent, padding=(14, 12), relief="ridge")
        frame.columnconfigure(0, weight=1)
        lbl = ttk.Label(frame, text=title, font=("Segoe UI", 12, "bold"))
        lbl.grid(row=0, column=0, sticky="w", pady=(0, 8))
        return frame

    def _build_reader_card(self, frame: ttk.Frame):
        body = ttk.Frame(frame)
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Connection:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.reader_conn_val = ttk.Label(body, text="Checking…")
        self.reader_conn_val.grid(row=0, column=1, sticky="w")

        ttk.Label(body, text="Reader:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.reader_name_val = ttk.Label(body, text="—", wraplength=320, justify="left")
        self.reader_name_val.grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _build_card_status_card(self, frame: ttk.Frame):
        body = ttk.Frame(frame)
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Card:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.card_present_val = ttk.Label(body, text="—")
        self.card_present_val.grid(row=0, column=1, sticky="w")

        ttk.Label(body, text="Last seen:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        self.last_seen_val = ttk.Label(body, text="—")
        self.last_seen_val.grid(row=1, column=1, sticky="w", pady=(6, 0))

    def _build_data_card(self, frame: ttk.Frame):
        body = ttk.Frame(frame)
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="ATR (hex):").grid(row=0, column=0, sticky="nw", padx=(0, 8))
        self.atr_val = ttk.Label(body, text="—", wraplength=360, justify="left")
        self.atr_val.grid(row=0, column=1, sticky="w")

        ttk.Label(body, text="UID (hex):").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=(6, 0))
        self.uid_hex_val = ttk.Label(body, text="—", wraplength=360, justify="left")
        self.uid_hex_val.grid(row=1, column=1, sticky="w", pady=(6, 0))

        ttk.Label(body, text="UID (dec):").grid(row=2, column=0, sticky="nw", padx=(0, 8), pady=(6, 0))
        self.uid_dec_val = ttk.Label(body, text="—", wraplength=360, justify="left")
        self.uid_dec_val.grid(row=2, column=1, sticky="w", pady=(6, 0))

    def _build_log_card(self, frame: ttk.Frame):
        ttk.Label(frame, text="Latest events (newest on bottom):").grid(row=1, column=0, sticky="w")

        self.log = tk.Text(frame, height=10, wrap="word")
        self.log.grid(row=2, column=0, sticky="nsew", pady=(8, 0))
        self.log.configure(state="disabled")

        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.log.yview)
        scroll.grid(row=2, column=1, sticky="ns", pady=(8, 0))
        self.log.configure(yscrollcommand=scroll.set)

    def _log(self, msg: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.log.configure(state="normal")
        self.log.insert("end", line)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._log("Log cleared.")

    def _set_error(self, msg: str):
        self.last_error = msg or ""
        self.err_lbl.config(text=self.last_error)

    def _set_reader_connected(self, connected: bool, name: str = "—"):
        if connected:
            self.reader_conn_val.config(text="CONNECTED")
            self.reader_name_val.config(text=name if name else "—")
        else:
            self.reader_conn_val.config(text="NOT CONNECTED")
            self.reader_name_val.config(text="—")

    def _set_card_present(self, present: bool):
        self.card_present_val.config(text="PRESENT" if present else "NOT PRESENT")

    def _poll(self):
        # clock
        self.clock_lbl.config(text=time.strftime("%H:%M:%S"))

        # detect readers
        try:
            rlist = readers()
            names = [str(r) for r in rlist]
            if names != self.last_reader_names:
                if names:
                    self._log("Reader connected: " + "; ".join(names))
                else:
                    self._log("Reader disconnected.")
                    # clear card data when reader goes away
                    self.atr_val.config(text="—")
                    self.uid_hex_val.config(text="—")
                    self.uid_dec_val.config(text="—")
                    self.last_uid_hex = None
                    self.last_seen_ts = None
                    self.last_seen_val.config(text="—")
                    self._set_card_present(False)
                self.last_reader_names = names

            if not rlist:
                self._set_reader_connected(False)
                self._set_error("")
                self.root.after(POLL_MS, self._poll)
                return

            # show "connected" with first reader
            reader = rlist[0]
            self._set_reader_connected(True, str(reader))
            self._set_error("")

        except Exception as e:
            self._set_reader_connected(False)
            self._set_error(f"PC/SC error: {e}")
            self.root.after(POLL_MS, self._poll)
            return

        # card polling
        try:
            conn = reader.createConnection()
            conn.connect()
            atr = bytes(conn.getATR())

            data, sw1, sw2 = conn.transmit(GET_UID)
            if (sw1, sw2) != (0x90, 0x00):
                # card might still be present but UID command not supported for this tech
                self._set_card_present(True)
                self._set_error(f"UID APDU failed: SW={sw1:02X}{sw2:02X}")
            else:
                uid = bytes(data)
                uid_hex = hexstr(uid)

                self._set_card_present(True)
                now_ts = time.strftime("%Y-%m-%d %H:%M:%S")
                self.last_seen_ts = now_ts
                self.last_seen_val.config(text=now_ts)

                # update displayed data
                self.atr_val.config(text=hexstr(atr))
                self.uid_hex_val.config(text=uid_hex)
                self.uid_dec_val.config(text=str(int_be(uid)))

                # log only on change
                if uid_hex != self.last_uid_hex:
                    self._log(f"Card detected | UID={uid_hex} (dec {int_be(uid)}) | ATR={hexstr(atr)}")
                    self.last_uid_hex = uid_hex

                self._set_error("")

        except NoCardException:
            self._set_card_present(False)
            self._set_error("")
            self.last_uid_hex = None
        except (CardConnectionException, OSError) as e:
            self._set_card_present(False)
            self._set_error(f"Card/reader error: {e}")
            self.last_uid_hex = None
        except Exception as e:
            self._set_card_present(False)
            self._set_error(f"Unexpected error: {e}")
            self.last_uid_hex = None

        # update last-seen label if we have one
        if self.last_seen_ts:
            self.last_seen_val.config(text=self.last_seen_ts)

        self.root.after(POLL_MS, self._poll)


def main():
    root = tk.Tk()

    # Use ttk theme if available
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    app = NFCApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
