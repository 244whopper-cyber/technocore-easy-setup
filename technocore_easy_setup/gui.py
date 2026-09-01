"""Tk desktop interface for Technocore Easy Setup."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from . import __version__
from .core import (
    IdentityError,
    LocalFileError,
    NetworkError,
    ProtocolError,
    contribution_message,
    create_contribution_proof,
    create_identity,
    did_from_private_key,
    import_identity,
    load_identity,
    post_signed_message,
    validate_room,
    verify_contribution_proof,
    write_new_json,
)
from .i18n import text
from .paths import identity_path


BG = "#f4f1e8"
CARD = "#fffdf8"
INK = "#172521"
MUTED = "#5c6b65"
GREEN = "#0c6b4f"
GREEN_DARK = "#084c39"
LINE = "#d8d5ca"
BLUE = "#315b78"


def primary_button(
    parent: tk.Misc,
    *,
    label: str,
    command: Callable[[], None],
    padx: int = 18,
    pady: int = 8,
) -> tk.Button:
    """Create a primary button that remains readable with macOS Aqua Tk.

    Aqua can ignore a ``tk.Button`` background while still applying its white
    foreground, which makes the label look disabled on a white button.  Use a
    dark label and a green focus outline on Aqua; retain the filled green style
    on Windows and other Tk platforms.
    """

    aqua = parent.tk.call("tk", "windowingsystem") == "aqua"
    return tk.Button(
        parent,
        text=label,
        command=command,
        padx=padx,
        pady=pady,
        bg=GREEN,
        fg=GREEN_DARK if aqua else "white",
        activebackground="#d4e7df" if aqua else GREEN_DARK,
        activeforeground=GREEN_DARK if aqua else "white",
        highlightbackground=GREEN,
        highlightcolor=GREEN_DARK,
        highlightthickness=2,
        borderwidth=1 if aqua else 0,
        relief="raised" if aqua else "flat",
        font=("TkDefaultFont", 10, "bold"),
        cursor="hand2",
    )


class FieldDialog(tk.Toplevel):
    """Small reusable modal form that returns string values."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        fields: list[tuple[str, str, str, bool]],
        submit_label: str,
        cancel_label: str,
    ) -> None:
        super().__init__(parent)
        self.result: dict[str, str] | None = None
        self.title(title)
        self.configure(bg=BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.entries: dict[str, tk.Widget] = {}
        frame = tk.Frame(self, bg=BG, padx=24, pady=20)
        frame.pack(fill="both", expand=True)
        first: tk.Widget | None = None
        for key, label, initial, multiline in fields:
            tk.Label(frame, text=label, bg=BG, fg=INK, anchor="w", font=("TkDefaultFont", 11, "bold")).pack(fill="x", pady=(8, 5))
            if multiline:
                widget: tk.Widget = tk.Text(frame, width=62, height=5, wrap="word", relief="solid", borderwidth=1)
                widget.insert("1.0", initial)
            else:
                show = "•" if "passphrase" in key else ""
                widget = tk.Entry(frame, width=64, show=show, relief="solid", borderwidth=1)
                widget.insert(0, initial)
            widget.pack(fill="x", ipady=6)
            self.entries[key] = widget
            first = first or widget
        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x", pady=(20, 0))
        tk.Button(buttons, text=cancel_label, command=self.destroy, padx=18, pady=8, relief="flat", bg="#e5e2d8", fg=INK).pack(side="right")
        primary_button(buttons, label=submit_label, command=self._submit).pack(side="right", padx=(0, 8))
        self.bind("<Escape>", lambda _event: self.destroy())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.update_idletasks()
        x = parent.winfo_rootx() + max(20, (parent.winfo_width() - self.winfo_width()) // 2)
        y = parent.winfo_rooty() + max(20, (parent.winfo_height() - self.winfo_height()) // 3)
        self.geometry(f"+{x}+{y}")
        if first:
            first.focus_set()
        self.wait_window(self)

    def _submit(self) -> None:
        values: dict[str, str] = {}
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                values[key] = widget.get("1.0", "end-1c")
            else:
                values[key] = widget.get()  # type: ignore[attr-defined]
        self.result = values
        self.destroy()


class EasySetupApp(tk.Tk):
    def __init__(self, key_path: Path | None = None) -> None:
        super().__init__()
        self.key_path = (key_path or identity_path()).expanduser().resolve()
        self.language = "ja"
        self.busy = False
        self.title("Technocore Easy Setup")
        self.geometry("940x730")
        self.minsize(820, 650)
        self.configure(bg=BG)
        self.option_add("*Font", ("TkDefaultFont", 10))
        self._build()

    def t(self, key: str) -> str:
        return text(self.language, key)

    def _build(self) -> None:
        for child in self.winfo_children():
            child.destroy()
        outer = tk.Frame(self, bg=BG, padx=34, pady=26)
        outer.pack(fill="both", expand=True)
        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(title_box, text=self.t("app_title"), bg=BG, fg=INK, font=("TkDefaultFont", 24, "bold"), anchor="w").pack(fill="x")
        tk.Label(title_box, text=self.t("subtitle"), bg=BG, fg=MUTED, font=("TkDefaultFont", 11), anchor="w").pack(fill="x", pady=(4, 0))
        lang_box = tk.Frame(header, bg=BG)
        lang_box.pack(side="right")
        tk.Label(lang_box, text=self.t("language"), bg=BG, fg=MUTED).pack(anchor="e")
        selector = ttk.Combobox(lang_box, values=["日本語", "English"], state="readonly", width=12)
        selector.set("日本語" if self.language == "ja" else "English")
        selector.pack(pady=(4, 0))
        selector.bind("<<ComboboxSelected>>", lambda _e: self._set_language(selector.get()))

        status = tk.Frame(outer, bg="#e4f2ec", padx=18, pady=13, highlightbackground="#bcd9cd", highlightthickness=1)
        status.pack(fill="x", pady=(20, 18))
        ready = self.key_path.exists()
        tk.Label(status, text="●", bg="#e4f2ec", fg=GREEN if ready else "#a56a12", font=("TkDefaultFont", 13)).pack(side="left")
        status_text = tk.Frame(status, bg="#e4f2ec")
        status_text.pack(side="left", padx=(10, 0), fill="x", expand=True)
        tk.Label(status_text, text=self.t("identity_ready" if ready else "identity_missing"), bg="#e4f2ec", fg=INK, font=("TkDefaultFont", 11, "bold"), anchor="w").pack(fill="x")
        tk.Label(status_text, text=self.t("key_local"), bg="#e4f2ec", fg=MUTED, anchor="w").pack(fill="x")
        if not ready:
            tk.Button(
                status,
                text=self.t("import_identity"),
                command=self.import_existing_identity,
                bg="#d4e7df",
                fg=GREEN_DARK,
                activebackground="#c6ddd3",
                relief="flat",
                padx=13,
                pady=7,
            ).pack(side="right")

        canvas = tk.Canvas(outer, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        body = tk.Frame(canvas, bg=BG)
        body.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        window = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        actions = [
            ("create", "create_desc", self.create_did),
            ("show", "show_desc", self.show_did),
            ("join", "join_desc", self.join_lobby),
            ("post", "post_desc", self.post_message),
            ("register", "register_desc", self.register_contribution),
            ("proof", "proof_desc", self.generate_proof),
        ]
        for index, (label_key, desc_key, command) in enumerate(actions):
            row, col = divmod(index, 2)
            body.grid_columnconfigure(col, weight=1, uniform="cards")
            card = tk.Frame(body, bg=CARD, padx=20, pady=17, highlightbackground=LINE, highlightthickness=1)
            card.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=8)
            tk.Label(card, text=self.t(label_key), bg=CARD, fg=INK, font=("TkDefaultFont", 13, "bold"), anchor="w").pack(fill="x")
            tk.Label(card, text=self.t(desc_key), bg=CARD, fg=MUTED, justify="left", wraplength=360, anchor="nw").pack(fill="both", expand=True, pady=(7, 13))
            button = primary_button(card, label=self.t("continue"), command=command, padx=16, pady=7)
            button.pack(anchor="e")

        footer = tk.Frame(body, bg=BG)
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        tk.Label(footer, text=f"{self.t('path_label')}: {self.key_path}", bg=BG, fg=MUTED, anchor="w", wraplength=700).pack(fill="x")
        tk.Label(footer, text=f"{self.t('disclaimer')}  •  v{__version__}", bg=BG, fg=MUTED, anchor="w").pack(fill="x", pady=(7, 16))

    def _set_language(self, selected: str) -> None:
        self.language = "ja" if selected == "日本語" else "en"
        self._build()

    def _fields(self, title_key: str, fields: list[tuple[str, str, str, bool]]) -> dict[str, str] | None:
        return FieldDialog(self, self.t(title_key), fields, self.t("continue"), self.t("cancel")).result

    def _need_identity(self) -> bool:
        if self.key_path.exists():
            return True
        messagebox.showwarning(self.t("error"), self.t("identity_needed"), parent=self)
        return False

    def _passphrase(self, title_key: str) -> str | None:
        values = self._fields(title_key, [("passphrase", self.t("passphrase"), "", False)])
        return values["passphrase"] if values else None

    def create_did(self) -> None:
        if self.key_path.exists():
            messagebox.showwarning(self.t("error"), self.t("identity_exists"), parent=self)
            return
        values = self._fields("create", [
            ("passphrase", self.t("passphrase"), "", False),
            ("confirm_passphrase", self.t("confirm_passphrase"), "", False),
        ])
        if not values:
            return
        if values["passphrase"] != values["confirm_passphrase"]:
            messagebox.showerror(self.t("error"), self.t("pass_mismatch"), parent=self)
            return
        try:
            did = create_identity(self.key_path, values["passphrase"])
        except (IdentityError, OSError) as error:
            self._show_error(error)
            return
        self._build()
        self._show_did_result(did, self.t("did_created"))

    def import_existing_identity(self) -> None:
        if self.key_path.exists():
            messagebox.showwarning(self.t("error"), self.t("identity_exists"), parent=self)
            return
        source = filedialog.askopenfilename(
            parent=self,
            title=self.t("select_identity"),
            filetypes=[("Encrypted PEM", "*.pem"), ("All files", "*")],
        )
        if not source:
            return
        passphrase = self._passphrase("import_identity")
        if passphrase is None:
            return
        try:
            did = import_identity(Path(source), self.key_path, passphrase)
        except IdentityError as error:
            self._show_error(error)
            return
        self._build()
        self._show_did_result(did, self.t("identity_imported"))

    def show_did(self) -> None:
        if not self._need_identity():
            return
        passphrase = self._passphrase("show")
        if passphrase is None:
            return
        try:
            did = did_from_private_key(load_identity(self.key_path, passphrase))
        except IdentityError as error:
            self._show_error(error)
            return
        self._show_did_result(did, "")

    def join_lobby(self) -> None:
        if not self._need_identity():
            return
        values = self._fields("join", [
            ("message", self.t("message"), self.t("join_default"), True),
            ("passphrase", self.t("passphrase"), "", False),
        ])
        if values:
            self._confirm_and_post("lobby", values["message"], values["passphrase"])

    def post_message(self) -> None:
        if not self._need_identity():
            return
        values = self._fields("post", [
            ("room", self.t("room"), "technocore", False),
            ("message", self.t("message"), "", True),
            ("passphrase", self.t("passphrase"), "", False),
        ])
        if values:
            self._confirm_and_post(values["room"], values["message"], values["passphrase"])

    def register_contribution(self) -> None:
        if not self._need_identity():
            return
        values = self._fields("register", [
            ("url", self.t("url"), "https://", False),
            ("description", self.t("description"), self.t("description_hint"), True),
            ("passphrase", self.t("passphrase"), "", False),
        ])
        if not values:
            return
        try:
            message = contribution_message(values["url"], values["description"])
        except ProtocolError as error:
            self._show_error(error)
            return
        self._confirm_and_post("technocore", message, values["passphrase"])

    def _confirm_and_post(self, room: str, message: str, passphrase: str) -> None:
        try:
            validate_room(room)
            private_key = load_identity(self.key_path, passphrase)
            did = did_from_private_key(private_key)
        except (IdentityError, ProtocolError) as error:
            self._show_error(error)
            return
        summary = f"{self.t('did_label')}: {did}\n{self.t('room')}: {room}\n\n{self.t('message')}:\n{message}"
        confirmed = messagebox.askokcancel(
            self.t("confirm_title"),
            f"{self.t('confirm_network')}\n\n{summary}",
            icon="warning",
            parent=self,
        )
        if not confirmed:
            return
        self._run_background(
            lambda: post_signed_message(private_key, room, message),
            lambda response: self._show_receipt(response),
        )

    def generate_proof(self) -> None:
        if not self._need_identity():
            return
        values = self._fields("proof", [
            ("url", self.t("url"), "https://", False),
            ("commit", self.t("commit"), "", False),
            ("passphrase", self.t("passphrase"), "", False),
        ])
        if not values:
            return
        output = filedialog.asksaveasfilename(
            parent=self,
            title=self.t("save_proof"),
            defaultextension=".json",
            initialfile="contribution-proof.json",
            filetypes=[("JSON", "*.json")],
        )
        if not output:
            return
        output_path = Path(output)
        if output_path.exists():
            messagebox.showwarning(self.t("error"), self.t("file_exists"), parent=self)
            return
        try:
            private_key = load_identity(self.key_path, values["passphrase"])
            proof = create_contribution_proof(private_key, values["url"], values["commit"])
            verify_contribution_proof(proof)
            write_new_json(output_path, proof)
        except (IdentityError, ProtocolError, LocalFileError) as error:
            self._show_error(error)
            return
        messagebox.showinfo(
            self.t("success"),
            f"{self.t('saved')}\n\n{output_path}\n\n{self.t('proof_public')}",
            parent=self,
        )

    def _run_background(self, job: Callable[[], Any], on_success: Callable[[Any], None]) -> None:
        if self.busy:
            return
        self.busy = True
        self.config(cursor="watch")
        def worker() -> None:
            try:
                result = job()
            except Exception as error:  # delivered to the UI thread below
                self.after(0, lambda error=error: self._finish_error(error))
            else:
                self.after(0, lambda: self._finish_success(result, on_success))
        threading.Thread(target=worker, daemon=True).start()

    def _finish_error(self, error: Exception) -> None:
        self.busy = False
        self.config(cursor="")
        self._show_error(error)

    def _finish_success(self, result: Any, callback: Callable[[Any], None]) -> None:
        self.busy = False
        self.config(cursor="")
        callback(result)

    def _show_error(self, error: Exception) -> None:
        known = isinstance(error, (IdentityError, ProtocolError, NetworkError, LocalFileError))
        detail = str(error) if known else "Unexpected local error. Please restart the app."
        messagebox.showerror(self.t("error"), detail, parent=self)

    def _show_did_result(self, did: str, note: str) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(self.t("success"))
        dialog.configure(bg=BG)
        dialog.transient(self)
        frame = tk.Frame(dialog, bg=BG, padx=25, pady=22)
        frame.pack(fill="both", expand=True)
        if note:
            tk.Label(frame, text=note, bg=BG, fg=INK, wraplength=560, justify="left").pack(fill="x", pady=(0, 14))
        tk.Label(frame, text=self.t("did_label"), bg=BG, fg=MUTED, anchor="w").pack(fill="x")
        entry = tk.Entry(frame, width=70, relief="solid", borderwidth=1)
        entry.insert(0, did)
        entry.configure(state="readonly", readonlybackground=CARD)
        entry.pack(fill="x", ipady=8, pady=(5, 12))
        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x")
        tk.Button(buttons, text=self.t("close"), command=dialog.destroy, relief="flat", bg="#e5e2d8", padx=16, pady=7).pack(side="right")
        tk.Button(buttons, text=self.t("copy"), command=lambda: self._copy(did), relief="flat", bg=GREEN, fg="white", padx=16, pady=7).pack(side="right", padx=(0, 8))

    def _show_receipt(self, response: dict[str, Any]) -> None:
        posted = response["posted"]
        receipt = {
            "did": posted.get("from"),
            "room": response.get("room"),
            "sequence": posted.get("seq"),
            "nonce": posted.get("nonce"),
            "timestamp": posted.get("ts") or posted.get("timestamp"),
            "message": posted.get("text"),
        }
        rendered = json.dumps(receipt, ensure_ascii=False, indent=2)
        dialog = tk.Toplevel(self)
        dialog.title(self.t("receipt"))
        dialog.configure(bg=BG)
        dialog.transient(self)
        frame = tk.Frame(dialog, bg=BG, padx=24, pady=20)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text=self.t("posted"), bg=BG, fg=GREEN, font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        box = tk.Text(frame, width=74, height=13, wrap="word", relief="solid", borderwidth=1)
        box.insert("1.0", rendered)
        box.configure(state="disabled")
        box.pack(fill="both", expand=True, pady=(12, 12))
        buttons = tk.Frame(frame, bg=BG)
        buttons.pack(fill="x")
        tk.Button(buttons, text=self.t("close"), command=dialog.destroy, relief="flat", bg="#e5e2d8", padx=16, pady=7).pack(side="right")
        tk.Button(buttons, text=self.t("copy"), command=lambda: self._copy(rendered), relief="flat", bg=GREEN, fg="white", padx=16, pady=7).pack(side="right", padx=(0, 8))

    def _copy(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.update_idletasks()


def main() -> None:
    app = EasySetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
