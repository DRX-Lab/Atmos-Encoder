import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, os

# -------------------- Main Window -------------------- #
root = tk.Tk()
root.title("Atmos Encoder GUI")
root.geometry("750x750")
root.configure(bg="#1b1b1b")

# -------------------- Tk Variables -------------------- #
input_type = tk.StringVar(value="file")
encoding_mode = tk.StringVar(value="DDP Atmos")
dialogue_intelligence = tk.StringVar(value="true")
drc = tk.StringVar(value="none")
disable_dbfs = tk.BooleanVar(value=False)
preferred_downmix = tk.StringVar(value="not_indicated")
warp_mode = tk.StringVar(value="normal")

# -------------------- Functions -------------------- #
def select_input_type():
    def set_type(ftype):
        input_type.set(ftype)
        type_window.destroy()
        select_input()

    type_window = tk.Toplevel(root)
    type_window.title("Select Input Type")
    type_window.geometry("300x100")
    type_window.configure(bg="#1b1b1b")
    tk.Label(type_window, text="Select Input Type", bg="#1b1b1b", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=10)
    tk.Button(type_window, text="File", width=12, command=lambda: set_type("file"), bg="#007acc", fg="white", relief='flat').pack(pady=2)
    tk.Button(type_window, text="Folder", width=12, command=lambda: set_type("folder"), bg="#007acc", fg="white", relief='flat').pack(pady=2)

def select_input():
    if input_type.get() == "file":
        path = filedialog.askopenfilename(title="Select Audio File",
                                          filetypes=[("Audio files", ".thd .mlp .wav .adm")])
    else:
        path = filedialog.askdirectory(title="Select Folder")
    
    if path:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, path)
        adv_frame.pack(fill='x', pady=15, padx=5)
        update_encoding_mode_state()

def update_encoding_mode_state():
    path = input_entry.get()
    if os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in [".wav", ".adm"]:
            encoding_mode.set("TrueHD Atmos")
        elif ext in [".mlp", ".thd"]:
            encoding_mode.set("DDP Atmos")
        toggle_encoding_mode()
    else:
        encoding_mode.set("DDP Atmos")  # default
        folder_window = tk.Toplevel(root)
        folder_window.title("Select Encoding Mode")
        folder_window.geometry("250x100")
        folder_window.configure(bg="#1b1b1b")
        tk.Label(folder_window, text="Select Encoding Mode for Folder", bg="#1b1b1b", fg="white").pack(pady=10)
        tk.Button(folder_window, text="DDP Atmos", width=12,
                  command=lambda: (encoding_mode.set("DDP Atmos"), toggle_encoding_mode(), folder_window.destroy())).pack(pady=2)
        tk.Button(folder_window, text="TrueHD Atmos", width=12,
                  command=lambda: (encoding_mode.set("TrueHD Atmos"), toggle_encoding_mode(), folder_window.destroy())).pack(pady=2)

def toggle_encoding_mode():
    bitrate_51_frame.pack_forget()
    bitrate_71_frame.pack_forget()
    spatial_frame.pack_forget()

    if encoding_mode.get() == "DDP Atmos":
        bitrate_51_frame.pack(fill='x', pady=6)
        bitrate_71_frame.pack(fill='x', pady=6)
    else:
        spatial_frame.pack(fill='x', pady=6)

def run_encoder():
    if not input_entry.get():
        messagebox.showerror("Error", "Please select an input")
        return
    
    cmd = ["python", os.path.join(os.getcwd(), "main.py"), "-i", input_entry.get()]

    if encoding_mode.get() == "DDP Atmos":
        cmd += ["-ba", str(get_bitrate_51()), "-b7", str(get_bitrate_71())]
    else:
        cmd += ["-t", "-sc", str(get_spatial())]

    cmd += ["-di", dialogue_intelligence.get()]
    cmd += ["-d", drc.get()]
    if disable_dbfs.get(): cmd.append("-nd")
    cmd += ["-pd", preferred_downmix.get()]
    cmd += ["-w", warp_mode.get()]

    try:
        subprocess.run(cmd, check=True)
        messagebox.showinfo("Success", "Encoding Completed Successfully!")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Encoder failed:\n{e}")

# -------------------- GUI Layout -------------------- #
main_frame = tk.Frame(root, bg="#1b1b1b")
main_frame.pack(padx=20, pady=20, fill='both', expand=True)

# Input selection
file_frame = tk.Frame(main_frame, bg="#1b1b1b")
file_frame.pack(fill='x', pady=8)
tk.Label(file_frame, text="Input:", width=20, anchor='w', bg="#1b1b1b", fg="white").pack(side='left', padx=5)
input_entry = tk.Entry(file_frame, width=50, bg="#2b2b2b", fg="white", insertbackground="white")
input_entry.pack(side='left', padx=5)
tk.Button(file_frame, text="Select Input Type", command=select_input_type, width=18, bg="#007acc", fg="white", relief='flat').pack(side='left', padx=5)

# Advanced Options
adv_frame = tk.LabelFrame(main_frame, text="Advanced Options", bg="#1b1b1b", fg="white", font=("Segoe UI", 10, "bold"))

# ---------- Helper to create slider ----------
def create_slider(frame, label_text, values, default_value):
    tk.Label(frame, text=label_text, width=25, anchor='w', bg="#1b1b1b", fg="white").pack(side='top', anchor='w', padx=5)
    var_index = values.index(default_value)
    display = tk.Label(frame, text=str(default_value), bg="#1b1b1b", fg="white", font=("Segoe UI", 10, "bold"))
    display.pack(side='top', anchor='w', padx=5)

    slider = tk.Scale(frame, from_=0, to=len(values)-1, orient='horizontal', showvalue=False, length=500,
                      bg="#1b1b1b", fg="white", highlightthickness=0, troughcolor="#2b2b2b", sliderrelief='flat')
    slider.set(var_index)
    slider.pack(fill='x', padx=10)

    tick_frame = tk.Frame(frame, bg="#1b1b1b")
    tick_frame.pack(fill='x', padx=10)
    for v in values:
        tk.Label(tick_frame, text=str(v), bg="#1b1b1b", fg="#aaaaaa", font=("Segoe UI", 8)).pack(side='left', expand=True)

    def update_label(val):
        display.config(text=str(values[int(float(val))]))
    slider.config(command=update_label)
    update_label(slider.get())
    return lambda: values[int(slider.get())]

# ---------- Sliders ----------
bitrate_51_frame = tk.Frame(adv_frame, bg="#1b1b1b")
get_bitrate_51 = create_slider(bitrate_51_frame, "Atmos 5.1 Bitrate (kbps):", [384, 448, 576, 640, 768, 1024], 1024)

bitrate_71_frame = tk.Frame(adv_frame, bg="#1b1b1b")
get_bitrate_71 = create_slider(bitrate_71_frame, "Atmos 7.1 Bitrate (kbps):", [1152, 1280, 1536, 1664], 1536)

spatial_frame = tk.Frame(adv_frame, bg="#1b1b1b")
get_spatial = create_slider(spatial_frame, "Spatial Clusters:", [12, 14, 16], 12)

# ---------- Other Options ----------
def create_option(frame, label_text, variable, options):
    tk.Label(frame, text=label_text, width=25, anchor='w', bg="#1b1b1b", fg="white").pack(side='left', padx=5)
    ttk.OptionMenu(frame, variable, variable.get(), *options).pack(side='left', padx=5)
    frame.pack(fill='x', pady=4)

drc = tk.StringVar(value="none")
create_option(tk.Frame(adv_frame, bg="#1b1b1b"), "DRC:", drc, ["none","film_standard","film_light","music_standard","music_light","speech"])

dialogue_intelligence = tk.StringVar(value="true")
create_option(tk.Frame(adv_frame, bg="#1b1b1b"), "Dialogue Intelligence:", dialogue_intelligence, ["true","false"])

disable_dbfs = tk.BooleanVar(value=False)
dbfs_frame = tk.Frame(adv_frame, bg="#1b1b1b")
tk.Label(dbfs_frame, text="Disable DBFS:", width=25, anchor='w', bg="#1b1b1b", fg="white").pack(side='left', padx=5)
tk.Checkbutton(dbfs_frame, variable=disable_dbfs, bg="#1b1b1b", fg="white").pack(side='left', padx=5)
dbfs_frame.pack(fill='x', pady=4)

preferred_downmix = tk.StringVar(value="not_indicated")
create_option(tk.Frame(adv_frame, bg="#1b1b1b"), "Preferred Downmix:", preferred_downmix, ["loro","ltrt","ltrt-pl2","not_indicated"])

warp_mode = tk.StringVar(value="normal")
create_option(tk.Frame(adv_frame, bg="#1b1b1b"), "Warp Mode:", warp_mode, ["normal","warping","prologiciix","loro"])

toggle_encoding_mode()

# ---------- Run Button ----------
tk.Button(main_frame, text="Run Encoder", command=run_encoder, bg="#00aaff", fg="white", font=("Segoe UI", 12, "bold"),
          width=25, relief='flat', activebackground="#0088cc").pack(pady=20)

# ---------- Footer ----------
binaries_note = tk.Label(root, text="Place required binaries/libs in 'binaries' (.exe/.dll/.so/.dylib)",
                         bg="#1b1b1b", fg="#555555", font=("Segoe UI", 8, "italic"))
binaries_note.pack(side='bottom', pady=3)
license_note = tk.Label(root, text="DRX-Lab | Uses certified Dolby Tech (user provides binaries)",
                        bg="#1b1b1b", fg="#555555", font=("Segoe UI", 8, "italic"))
license_note.pack(side='bottom', pady=3)

root.mainloop()