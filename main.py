"""Liminal Backrooms Generator — CustomTkinter UI. See style/interface.md."""

import io
import queue
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

import generator
import postprocess
import providers
import storage

BG_WINDOW = "#141414"
BG_IMAGE = "#0d0d0d"
BG_BAR = "#1a1a1a"
BG_MESSAGE = "#262626"
BUTTON = "#2a2a2a"
BUTTON_HOVER = "#3a3a3a"
TEXT = "#d8d8d8"
TEXT_DIM = "#8a8a8a"
CUSTOM_LABEL = "custom…"
FONT_SIZE = 16  # main window controls
SETTINGS_FONT_SIZE = 15
BUTTON_HEIGHT = 44
FIELD_HEIGHT = 38  # settings fields and menus

NO_TOKEN_MESSAGE = "Add an API token in ⚙"
ERROR_DURATION = 5000
SAVED_DURATION = 2000


def button(parent, font_size=FONT_SIZE, **kwargs):
    kwargs.setdefault("height", BUTTON_HEIGHT)
    return ctk.CTkButton(parent, fg_color=BUTTON, hover_color=BUTTON_HOVER, text_color=TEXT,
                         text_color_disabled=TEXT_DIM, corner_radius=6, font=ctk.CTkFont(size=font_size), **kwargs)


def fit_size(image_size, box_size):
    """Largest size with the image's ratio that fits in the box."""
    (iw, ih), (bw, bh) = image_size, box_size
    scale = min(bw / iw, bh / ih)
    return max(1, int(iw * scale)), max(1, int(ih * scale))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG_WINDOW)
        self.config_data = storage.load_config()
        self.history = storage.load_history()
        self.fragments = generator.load_fragments()
        self.tasks = queue.Queue()  # callables to run on the UI thread
        self.busy = False
        self.image = None  # PIL image currently shown
        self.image_bytes = None
        self.metadata = None
        self.slug = None
        self.message_job = None
        self.resize_job = None
        self.settings = None

        self.title("Liminal")
        self.geometry(self.config_data["geometry"])
        self.minsize(480, 330)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.image_frame = ctk.CTkFrame(self, fg_color=BG_IMAGE, corner_radius=0)
        self.image_frame.grid(row=0, column=0, sticky="nsew")
        self.image_label = ctk.CTkLabel(self.image_frame, text="")
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")
        self.message = ctk.CTkLabel(self.image_frame, text="", fg_color=BG_MESSAGE, text_color=TEXT,
                                    corner_radius=6, padx=12, font=ctk.CTkFont(size=FONT_SIZE))
        self.image_frame.bind("<Configure>", self.on_resize)

        bar = ctk.CTkFrame(self, fg_color=BG_BAR, corner_radius=0)
        bar.grid(row=1, column=0, sticky="ew")
        self.generate_button = button(bar, text="Generate", width=150, command=self.generate)
        self.generate_button.pack(side="left", padx=(10, 6), pady=8)
        self.save_button = button(bar, text="Save", width=110, command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=6, pady=8)
        button(bar, text="⚙", width=BUTTON_HEIGHT, font_size=22, command=self.open_settings).pack(
            side="right", padx=10, pady=8)

        self.bind("<space>", self.generate)
        self.bind("<Return>", self.generate)
        self.bind("<Control-s>", self.save)
        self.bind("<Escape>", lambda _e: self.quit_app())
        self.protocol("WM_DELETE_WINDOW", self.quit_app)

        self.refresh_token_state()
        self.after(100, self.poll_tasks)

    # --- threading helpers -------------------------------------------

    def poll_tasks(self):
        while not self.tasks.empty():
            self.tasks.get()()
        self.after(100, self.poll_tasks)

    def run_in_background(self, work, on_done):
        """Run work() in a thread, then on_done(result_or_exception) on the UI thread."""
        def worker():
            try:
                result = work()
            except Exception as error:  # reported to the UI, never crashes the thread silently
                result = error
            self.tasks.put(lambda: on_done(result))
        threading.Thread(target=worker, daemon=True).start()

    # --- messages and image display ----------------------------------

    def show_message(self, text, duration=None):
        if self.message_job:
            self.after_cancel(self.message_job)
            self.message_job = None
        if not text:
            self.message.place_forget()
            return
        self.message.configure(text=text)
        self.message.place(relx=0.5, rely=0.5, anchor="center")
        if duration:
            self.message_job = self.after(duration, lambda: self.show_message(None))

    def on_resize(self, _event=None):
        if self.resize_job:
            self.after_cancel(self.resize_job)
        self.resize_job = self.after(50, self.render_image)

    def render_image(self):
        self.resize_job = None
        if self.image is None:
            return
        box = (self.image_frame.winfo_width(), self.image_frame.winfo_height())
        if min(box) < 2:
            return
        size = fit_size(self.image.size, box)
        self.image_label.configure(image=ctk.CTkImage(light_image=self.image, dark_image=self.image, size=size))

    # --- generation ----------------------------------------------------

    def refresh_token_state(self):
        provider, _model_id, _custom = storage.active_model(self.config_data)
        token, _from_env = storage.get_token(self.config_data, provider)
        if token:
            if self.message.cget("text") == NO_TOKEN_MESSAGE:
                self.show_message(None)
            if not self.busy:
                self.generate_button.configure(state="normal")
        else:
            self.generate_button.configure(state="disabled")
            self.show_message(NO_TOKEN_MESSAGE)

    def generate(self, _event=None):
        if self.busy or self.generate_button.cget("state") == "disabled":
            return
        provider, model_id, custom = storage.active_model(self.config_data)
        token, _from_env = storage.get_token(self.config_data, provider)
        if custom and not model_id:
            self.show_message("Set a custom model in ⚙", ERROR_DURATION)
            return
        self.busy = True
        self.generate_button.configure(state="disabled")
        self.show_message("generating…")

        def work():
            result = generator.new_prompt(self.fragments, self.history)
            output = providers.generate_image(provider, model_id, result.prompt, result.seed, token, custom)
            look = postprocess.random_params()
            image = postprocess.analog_look(Image.open(io.BytesIO(output.data)), look)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            generator.record(self.history, result)
            storage.save_history(self.history)
            metadata = {
                "prompt": result.prompt,
                "provider": provider,
                "model": model_id,
                "seed": output.seed,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "fragments": result.fragments,
                "postprocess": {"name": postprocess.NAME, **look},
            }
            return image, buffer.getvalue(), metadata, result.slug

        self.run_in_background(work, self.on_generated)

    def on_generated(self, result):
        self.busy = False
        self.refresh_token_state()
        if isinstance(result, providers.ProviderError):
            self.show_message(str(result), ERROR_DURATION)
            return
        if isinstance(result, Exception):
            self.show_message(f"error: {result}"[:120], ERROR_DURATION)
            return
        self.image, self.image_bytes, self.metadata, self.slug = result
        self.show_message(None)
        self.save_button.configure(state="normal")
        self.render_image()

    # --- saving --------------------------------------------------------

    def save(self, _event=None):
        if self.image_bytes is None:
            return
        image_bytes, metadata = self.image_bytes, self.metadata  # snapshot: a new generation may start meanwhile
        filename = storage.suggested_filename(self.slug)
        initial_dir = Path(self.config_data["last_dir"])
        if not initial_dir.is_dir():
            initial_dir = storage.DEFAULT_SAVE_DIR
            initial_dir.mkdir(parents=True, exist_ok=True)

        def write(path):
            if isinstance(path, Exception):
                self.show_message(f"error: {path}"[:120], ERROR_DURATION)
            elif path:
                self.run_in_background(lambda: storage.save_image(image_bytes, path, metadata), self.on_saved)

        if storage.zenity_available():
            self.run_in_background(lambda: storage.ask_save_path_zenity(initial_dir, filename), write)
        else:
            write(filedialog.asksaveasfilename(parent=self, initialdir=initial_dir, initialfile=filename,
                                               defaultextension=".png", filetypes=[("PNG images", "*.png")]))

    def on_saved(self, result):
        if isinstance(result, Exception):
            self.show_message(f"error: {result}"[:120], ERROR_DURATION)
            return
        self.config_data["last_dir"] = str(Path(result).parent)
        storage.save_config(self.config_data)
        self.show_message("saved", SAVED_DURATION)

    # --- settings and exit -------------------------------------------

    def open_settings(self):
        if self.settings and self.settings.winfo_exists():
            self.settings.focus()
            return
        self.settings = SettingsWindow(self)

    def on_settings_closed(self):
        storage.save_config(self.config_data)
        self.refresh_token_state()

    def quit_app(self):
        self.config_data["geometry"] = self.geometry().split("+")[0]
        storage.save_config(self.config_data)
        self.destroy()


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, app):
        super().__init__(app, fg_color=BG_WINDOW)
        self.app = app
        self.config_data = app.config_data
        self.provider = self.config_data["provider"]
        self.title("Settings")
        self.resizable(False, False)
        self.transient(app)
        self.grid_columnconfigure(1, weight=1)
        font = ctk.CTkFont(size=SETTINGS_FONT_SIZE)
        menu_style = dict(fg_color=BUTTON, button_color=BUTTON, button_hover_color=BUTTON_HOVER, text_color=TEXT,
                          height=FIELD_HEIGHT, font=font, dropdown_font=font)

        def label(text, row):
            ctk.CTkLabel(self, text=text, text_color=TEXT_DIM, font=font).grid(row=row, column=0, sticky="w", padx=(12, 8),
                                                                     pady=6)

        label("Provider", 0)
        self.provider_menu = ctk.CTkOptionMenu(
            self, values=[p.label for p in providers.PROVIDERS.values()], command=self.on_provider_selected,
            width=320, **menu_style)
        self.provider_menu.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=(12, 6))

        label("API token", 1)
        self.token_entry = ctk.CTkEntry(self, show="•", width=270, height=FIELD_HEIGHT, font=font)
        self.token_entry.grid(row=1, column=1, sticky="ew", pady=6)
        self.token_entry.bind("<KeyRelease>", self.on_token_typed)
        self.eye_button = button(self, text="👁", width=FIELD_HEIGHT, height=FIELD_HEIGHT, font_size=SETTINGS_FONT_SIZE,
                                 command=self.toggle_token_visibility)
        self.eye_button.grid(row=1, column=2, padx=(4, 12), pady=6)
        self.env_label = ctk.CTkLabel(self, text="(from env)", text_color=TEXT_DIM, font=font)

        label("Model", 3)
        self.model_menu = ctk.CTkOptionMenu(self, values=[""], command=self.on_model_selected, **menu_style)
        self.model_menu.grid(row=3, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=6)
        self.custom_entry = ctk.CTkEntry(self, placeholder_text="model id, e.g. owner/name", height=FIELD_HEIGHT,
                                         font=font)

        self.verify_button = button(self, text="Verify", width=100, height=FIELD_HEIGHT, font_size=SETTINGS_FONT_SIZE,
                                     command=self.verify)
        self.verify_button.grid(row=5, column=1, sticky="w", pady=(6, 4))
        self.verify_label = ctk.CTkLabel(self, text="", text_color=TEXT_DIM, font=font)
        self.verify_label.grid(row=6, column=1, columnspan=2, sticky="w", pady=(0, 12))

        self.load_provider()
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self.focus)  # CTkToplevel may otherwise open behind the main window

    # Model menu labels <-> ids for the current provider
    def model_labels(self):
        return {f"{m.label} — {m.price}": m.id for m in providers.models_for(self.provider)}

    def load_provider(self):
        self.provider_menu.set(providers.PROVIDERS[self.provider].label)
        token, from_env = storage.get_token(self.config_data, self.provider)
        self.from_env = from_env
        self.token_entry.configure(state="normal", show="•")
        self.token_entry.delete(0, "end")
        self.token_entry.insert(0, token)
        if from_env:
            self.token_entry.configure(state="disabled")
            self.env_label.grid(row=2, column=1, sticky="w")
        else:
            self.env_label.grid_remove()

        labels = self.model_labels()
        self.model_menu.configure(values=list(labels) + [CUSTOM_LABEL])
        model_id = self.config_data["models"].get(self.provider) or next(iter(labels.values()))
        if model_id == providers.CUSTOM:
            self.model_menu.set(CUSTOM_LABEL)
        else:
            self.model_menu.set(next((k for k, v in labels.items() if v == model_id), next(iter(labels))))
        self.custom_entry.delete(0, "end")
        custom = self.config_data["custom_models"].get(self.provider, "")
        if custom:
            self.custom_entry.insert(0, custom)
        self.update_custom_visibility()
        self.verify_label.configure(text="")

    def commit(self):
        """Write the current fields of the shown provider into the config."""
        if not self.from_env:
            token = self.token_entry.get().strip()
            if token:
                self.config_data["tokens"][self.provider] = token
            else:
                self.config_data["tokens"].pop(self.provider, None)
        selected = self.model_menu.get()
        self.config_data["models"][self.provider] = (
            providers.CUSTOM if selected == CUSTOM_LABEL else self.model_labels().get(selected, providers.DEFAULT_MODEL)
        )
        self.config_data["custom_models"][self.provider] = self.custom_entry.get().strip()
        self.config_data["provider"] = self.provider

    def on_provider_selected(self, label):
        self.commit()
        self.provider = next(p.key for p in providers.PROVIDERS.values() if p.label == label)
        self.load_provider()

    def on_token_typed(self, _event=None):
        token = self.token_entry.get().strip()
        detected = providers.detect_provider(token)
        if detected and detected != self.provider:
            self.config_data["tokens"][detected] = token  # the pasted token belongs to another provider
            self.provider = detected
            self.load_provider()

    def toggle_token_visibility(self):
        self.token_entry.configure(show="" if self.token_entry.cget("show") else "•")

    def on_model_selected(self, _label):
        self.update_custom_visibility()

    def update_custom_visibility(self):
        if self.model_menu.get() == CUSTOM_LABEL:
            self.custom_entry.grid(row=4, column=1, columnspan=2, sticky="ew", padx=(0, 12), pady=6)
        else:
            self.custom_entry.grid_remove()

    def verify(self):
        self.commit()
        token, _from_env = storage.get_token(self.config_data, self.provider)
        if not token:
            self.verify_label.configure(text="no token")
            return
        self.verify_button.configure(state="disabled")
        self.verify_label.configure(text="checking…")
        self.app.run_in_background(lambda: providers.verify_token(self.provider, token), self.on_verified)

    def on_verified(self, result):
        if not self.winfo_exists():
            return
        self.verify_button.configure(state="normal")
        self.verify_label.configure(text=str(result) if isinstance(result, Exception) else "ok")

    def close(self):
        self.commit()
        self.app.on_settings_closed()
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    App().mainloop()
