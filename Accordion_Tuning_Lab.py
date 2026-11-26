"""Accordeon Zwevingslab — bestaande functies plus gemeten accordeon-emulatie.
Vereist: numpy, sounddevice; optioneel: mido, python-rtmidi (MIDI).
Start: py -3.12 accordeon_zwevingslab.py
"""
import json
import os
import sys
import shutil
from pathlib import Path
import math
import re
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import numpy as np
    import sounddevice as sd
except ImportError as exc:
    raise SystemExit('Installeer eerst: py -3.12 -m pip install numpy sounddevice\n' + str(exc))
try:
    import mido
    mido.set_backend("mido.backends.rtmidi")
except ImportError:
    mido = None


TRANSLATIONS = {'Accordeon Zwevingslab — versie 3.4': 'Accordion Tuning Lab — version 3.4', 'Accordeon Zwevingslab': 'Accordion Tuning Lab', 'Kies een testtoon of verbind MIDI.': 'Choose a test note or connect MIDI.', 'Geen MIDI-bestand': 'No MIDI file', 'Drie stemprofielen — klik om te kiezen': 'Three tuning profiles — click to select', 'Drawbars (sinusklank)': 'Drawbars (sine tone)', 'Registers en referentie': 'Reeds and reference', 'Testtonen (ingedrukt houden)': 'Test notes (hold down)', 'Klankbron: ': 'Sound source: ', 'Profiel opslaan': 'Save profile', 'Kies eerst een van de drie profielvakken.\nAls je het profiel al hebt bewerkt, gebruik dan Profiel opslaan...': 'Select one of the three profile slots first.\nIf you have already edited the profile, use Save profile...', 'Profiel bijwerken': 'Update profile', 'Onjuist notenbereik': 'Incorrect note range', 'Referentie buiten 400–480 Hz': 'Reference outside 400–480 Hz', 'Ongeldige registerinstellingen': 'Invalid reed settings', 'Installeer mido: py -3.12 -m pip install mido': 'MIDI library unavailable (mido).', 'MIDI geladen. Klik op Play.': 'MIDI loaded. Click Play.', 'Audio actief. Speel via MIDI of met de testknoppen.': 'Audio active. Play via MIDI or the test buttons.', 'MIDI niet beschikbaar: installeer mido en python-rtmidi.': 'MIDI unavailable: mido and python-rtmidi required.', 'Installeer: py -3.12 -m pip install mido python-rtmidi': 'MIDI libraries unavailable.', 'Er is geen MIDI-ingang geselecteerd.': 'No MIDI input selected.', 'Profiel laden': 'Load profile', 'Accordeon (9 meetnoten)': 'Accordion (9 measured notes)', 'Sinus + drawbars': 'Sine + drawbars', 'Opslaan mislukt': 'Save failed', 'Profiel laden mislukt': 'Profile load failed', 'Ongeldige centwaarden': 'Invalid cent values', 'MIDI laden mislukt': 'MIDI load failed', 'Zweving: ': 'Beating: ', 'Laden mislukt': 'Load failed', 'Gebruik 400–480 Hz': 'Use 400–480 Hz', 'Grafiek vergroten (F11)': 'Expand graph (F11)', '■ Alle noten uit': '■ All notes off', 'Max. cent': 'Max. cents', 'Alleen sinus': 'Sine only', 'Driekorige modus': 'Three-reed mode', 'Bewerk curve:': 'Edit curve:', 'Toon zweving (Hz)': 'Show beating (Hz)', 'Ongeldige waarde': 'Invalid value', 'Gebruik een afwijking binnen ±100 cents.': 'Use a deviation within ±100 cents.', 'MIDI-invoer': 'MIDI input', 'MIDI-bestand': 'MIDI file', 'MIDI-bestanden': 'MIDI files', 'Vernieuwen': 'Refresh', 'Verbinden': 'Connect', 'Pauze': 'Pause', 'Laden': 'Load', 'Klankbron': 'Sound source', 'Accordeon': 'Accordion', 'Instellen': 'Set', 'Kopieer': 'Copy', 'Spiegel': 'Mirror', 'Opslaan...': 'Save...', 'Laden...': 'Load...', 'Zwevingsprofiel': 'Tuning profile', '(leeg)': '(empty)', 'Audiofout': 'Audio error', 'MIDI-fout': 'MIDI error', 'Referentie': 'Reference', 'Geen boventoonprofiel beschikbaar': 'No harmonic profile available', 'Audio nog niet gestart': 'Audio not started', 'Audio actief': 'Audio active'}
PREF = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'Accordion Tuning Lab' / 'settings.json'
try:
    LANG = json.loads(PREF.read_text(encoding='utf-8')).get('language', 'en')
except (OSError, ValueError):
    LANG = 'en'
BUNDLED_PROFILES = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'Profiles'
PROFILE_DIR = PREF.parent / 'Profiles'
try:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    for source in BUNDLED_PROFILES.glob('*.json'):
        target = PROFILE_DIR / source.name
        if not target.exists(): shutil.copyfile(source, target)
except OSError:
    PROFILE_DIR = Path.home()
def tr(text):
    return TRANSLATIONS.get(text, text) if LANG == 'en' else text

LOW, HIGH = 48, 96  # C3 - C7
SR = 44100
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Boventoonmetingen uit de opname "accordeon meer noten.WAV".
# Gemeten op negen afzonderlijke noten; dB relatief aan de grondtoon.
# Tussenliggende MIDI-noten krijgen lineair in dB geïnterpoleerde profielen.
# Buiten het meetbereik wordt het dichtstbijzijnde profiel gebruikt.
ACCORDION_PROFILES_DB = {60: [0.0, -27.14, -13.76, -15.35, -15.63, -17.17, -16.66, -19.07, -12.05, -30.67, -13.87, -37.82, -17.2, -24.22, -20.55, -16.87, -17.07, -40.22, -29.75, -22.13], 64: [0.0, -32.16, -7.61, -16.1, -5.97, -15.76, -20.99, -23.67, -21.54, -24.39, -27.11, -43.38, -24.99, -16.74, -22.91, -25.23, -35.04, -32.42, -32.0, -28.14], 68: [0.0, -30.22, -16.32, -17.87, -20.03, -21.16, -19.66, -45.58, -22.08, -27.45, -15.92, -23.18, -25.15, -52.54, -32.03, -38.69, -33.84, -38.36, -52.46, -43.71], 72: [0.0, -17.93, -5.68, -10.63, -14.37, -35.67, -26.22, -22.98, -21.65, -20.28, -25.52, -30.41, -37.15, -36.15, -45.74, -36.82, -49.38, -45.4, -49.24, -53.0], 76: [0.0, -16.19, -5.52, -13.63, -13.36, -18.66, -8.32, -12.7, -20.75, -27.71, -31.7, -30.33, -35.68, -32.85, -37.9, -44.58, -42.55, -40.65, -47.69, -49.84], 80: [0.0, -10.36, -8.15, -18.95, -30.02, -17.03, -21.77, -21.84, -41.33, -42.8, -34.42, -33.21, -42.84, -48.54, -46.26, -48.54, -59.21, -65.0, -65.0, -65.0], 84: [0.0, -7.38, -5.51, -12.9, -8.51, -12.23, -15.04, -23.71, -44.09, -31.66, -37.98, -37.05, -42.62, -46.96, -52.91, -65.0, -59.44, -56.49, -65.0, -65.0], 88: [0.0, -0.91, 8.82, -1.88, 5.49, -9.82, -16.92, -22.94, -30.09, -44.76, -35.0, -46.59, -50.15, -43.22, -52.45, -53.02, -65.0, -65.0, -65.0, -65.0], 91: [0.0, -22.04, -9.23, -8.9, -16.89, -35.9, -31.01, -39.68, -41.98, -65.0, -55.53, -59.77, -61.66, -65.0, -65.0, -65.0, -65.0, -65.0, -65.0, -65.0]}
TABLE_SIZE = 2048

def accordion_profile(note):
    keys = sorted(ACCORDION_PROFILES_DB)
    if note <= keys[0]:
        return np.array(ACCORDION_PROFILES_DB[keys[0]], dtype=np.float64)
    if note >= keys[-1]:
        return np.array(ACCORDION_PROFILES_DB[keys[-1]], dtype=np.float64)
    for low, high in zip(keys, keys[1:]):
        if low <= note <= high:
            weight = (note-low)/(high-low)
            return ((1-weight)*np.array(ACCORDION_PROFILES_DB[low]) +
                    weight*np.array(ACCORDION_PROFILES_DB[high]))
    raise ValueError(tr('Geen boventoonprofiel beschikbaar'))


def note_name(n):
    return f'{NOTE_NAMES[n % 12]}{n // 12 - 1}'

class AudioEngine:
    def __init__(self):
        self.lock = threading.RLock()
        self.active = {}  # midi note -> [phase1, phase2, amplitude, envelope, released]
        self.cents = np.zeros(128, dtype=np.float64)
        self.current_cents = np.zeros((3,128))
        self.targets = np.zeros((3,128))
        self.reference = 440.
        self.gains = np.array([0.,1.,1.])
        self.current_gains = self.gains.copy()
        self.volume = 0.22
        self.harmonics = np.array([1., 0., 0., 0., 0.], dtype=np.float64)
        self.stream = None
        self.mode = 'sinus'
        self.accordion_tables = self.build_accordion_tables()
        self.status = tr('Audio nog niet gestart')

    @staticmethod
    def build_accordion_tables():
        # Bandbegrensde golfvorm per toonhoogte: voorkomt aliasing.
        phase = 2 * np.pi * np.arange(TABLE_SIZE) / TABLE_SIZE
        tables = {}
        for note in range(128):
            freq = 440. * 2. ** ((note - 69) / 12.)
            # Reserve voor de maximale verstemming van 100 cents.
            count = min(20,
                        max(1, int((SR * .48) / (freq * (480/440) * 2 ** (100 / 1200)))))
            waveform = np.zeros(TABLE_SIZE)
            for n, amplitude in enumerate(np.power(10., accordion_profile(note)[:count] / 20.), 1):
                waveform += amplitude * np.sin(n * phase)
            peak = max(1., float(np.max(np.abs(waveform))))
            tables[note] = (waveform / peak).astype(np.float64)
        return tables

    @staticmethod
    def table_signal(table, phases):
        positions = np.mod(phases, 2 * np.pi) * (TABLE_SIZE / (2 * np.pi))
        left = positions.astype(np.int32)
        frac = positions - left
        return table[left] * (1 - frac) + table[(left + 1) % TABLE_SIZE] * frac

    def start(self):
        if self.stream is not None:
            return
        self.stream = sd.OutputStream(samplerate=SR, channels=2, dtype='float32',
                                      blocksize=256, latency='low', callback=self.callback)
        self.stream.start()
        self.status = tr('Audio actief')

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None

    def note_on(self, note, velocity=100):
        if 0 <= note <= 127:
            with self.lock:
                self.current_cents[:,note] = self.targets[:,note]
                self.active[note] = [np.zeros(3), max(.03, velocity/127.), 0., False]

    def note_off(self, note):
        with self.lock:
            if note in self.active:
                self.active[note][3] = True

    def all_off(self):
        with self.lock:
            self.active.clear()

    def set_profile(self, values, lower=None, reference=440., gains=(0.,1.,1.)):
        with self.lock:
            self.targets[2,LOW:HIGH+1] = values
            self.targets[0,LOW:HIGH+1] = lower if lower is not None else 0.
            self.reference = reference
            self.gains = np.asarray(gains, dtype=float)

    def set_harmonics(self, overtone_levels):
        with self.lock:
            self.harmonics = np.array([1.] + [float(x) / 100. for x in overtone_levels], dtype=np.float64)

    def set_mode(self, mode):
        with self.lock:
            self.mode = mode
            self.active.clear()

    def callback(self, outdata, frames, time_info, status):
        mix = np.zeros(frames)
        with self.lock:
            step = min(1., frames/(SR*.020))
            gains = self.current_gains + (self.gains-self.current_gains)*step
            ramps = np.linspace(self.current_gains, gains, frames).T
            self.current_gains = gains
            for note, voice in list(self.active.items()):
                phases, amp, env, released = voice
                base = self.reference * 2**((note-69)/12)
                old = self.current_cents[:,note]
                new = old + (self.targets[:,note]-old)*step
                curves = np.linspace(old,new,frames).T
                self.current_cents[:,note] = new
                sig = np.zeros(frames)
                for k in range(3):
                    freq = base * np.exp2(curves[k]/1200)
                    increments = 2*np.pi*freq/SR
                    phase = phases[k]+np.cumsum(increments)-increments
                    phases[k] = (phases[k]+sum(increments))%(2*np.pi)
                    if not np.any(ramps[k]):
                        continue
                    if self.mode == 'accordion':
                        wave = self.table_signal(self.accordion_tables[note],phase)
                    else:
                        wave = np.zeros(frames)
                        for h,level in enumerate(self.harmonics,1):
                            if level and h*max(freq[0],freq[-1]) < SR/2:
                                wave += level*np.sin(h*phase)
                        wave /= max(1.,sum(self.harmonics))
                    sig += ramps[k]*wave
                envelope = (np.maximum(0.,env-np.arange(1,frames+1)/(SR*.08)) if released else
                            np.minimum(1.,env+np.arange(1,frames+1)/(SR*.012)))
                mix += .5*sig*envelope*amp
                voice[2] = float(envelope[-1])
                if released and voice[2]<=0:
                    del self.active[note]
            mix = np.tanh(mix*self.volume)
        outdata[:] = mix[:,None]

class App:
    def __init__(self, root):
        self.root = root
        root.title(tr('Accordeon Zwevingslab — versie 3.4'))
        root.geometry('1180x780')
        root.minsize(940, 580)
        self.audio = AudioEngine()
        self.values = [round(2 + 10 * (i / (HIGH-LOW))**1.15, 2) for i in range(HIGH-LOW+1)]
        self.lower = [-v for v in self.values]
        self.reference = 440.
        self.ref_var = tk.StringVar(value='440.00')
        self.reference_initialized = False
        self.extended = tk.BooleanVar(value=False)
        self.enabled = [tk.BooleanVar(value=True) for _ in range(3)]
        self.levels = [tk.DoubleVar(value=100) for _ in range(3)]
        self.edit_register = tk.StringVar(value='M+')
        self.hz_value = tk.StringVar()
        self.selected = 69
        self.dragging = False
        self.last_drag = None
        self.midi_port = None
        self.midi_queue = queue.Queue()
        self.midi_devices = []
        self.test_notes = set()
        self.midi_held = set()  # ingedrukte MIDI-noten voor grafiekmarkering
        self.range_max = tk.DoubleVar(value=30)
        self.volume = tk.DoubleVar(value=22)
        self.drawbar_vars = [tk.DoubleVar(value=v) for v in (30, 15, 5, 0)]
        self.audio.set_harmonics([v.get() for v in self.drawbar_vars])
        self.sound_mode = tk.StringVar(value='accordion')
        self.audio.set_mode('accordion')
        self.selected_value = tk.StringVar()
        self._syncing_entry = False
        self._entry_editing = False
        self.device_name = tk.StringVar()
        self.status = tk.StringVar(value=tr('Kies een testtoon of verbind MIDI.'))
        self.profile_slots = [None, None, None]
        self.active_slot = None
        self.profile_buttons = []
        self.midi_events = []
        self.midi_index = 0
        self.midi_position = 0.
        self.midi_started = 0.
        self.midi_playing = False
        self.midi_paused = False
        self.midi_notes = set()
        self.midi_title = tk.StringVar(value=tr('Geen MIDI-bestand'))
        self.build_ui()
        self.refresh_devices()
        self.redraw()
        root.after(25, self.poll_midi)
        root.after(10, self.poll_file_player)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=2)
        outer.pack(fill='both', expand=True)
        header = ttk.Frame(outer)
        header.pack(fill='x', pady=0)
        ttk.Button(header, text='NL / EN', command=self.switch_language).pack(side='right')
        heading = ttk.Frame(header)
        heading.pack(side='left', fill='x', expand=True)
        ttk.Label(heading, text=tr('Accordeon Zwevingslab'), font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Button(header, text=tr('Grafiek vergroten (F11)'), command=self.toggle_controls).pack(side='right')
        controls = ttk.Frame(outer)
        controls.pack(fill='x', pady=0)
        self.controls = controls
        right = ttk.Frame(controls); right.pack(side='left', fill='both', expand=True, padx=3)
        left = ttk.Frame(controls); left.pack(side='left', fill='both', expand=True, padx=3)
        editor = ttk.Frame(controls); editor.pack(side='left', fill='both', expand=True, padx=3)
        self.show_hz = tk.BooleanVar(value=True)
        profile_row = ttk.Frame(right); profile_row.pack(fill='x')
        slots = ttk.LabelFrame(profile_row, text=tr('Drie stemprofielen — klik om te kiezen'), padding=2)
        slots.pack(side='left', fill='both', expand=True, pady=0)
        for i in range(3):
            line = ttk.Frame(slots)
            line.pack(fill='x', pady=1)
            button = tk.Button(line, text=(f'{i+1}: (empty)' if LANG == "en" else f'{i+1}: (leeg)'), width=15,
                               anchor='w', command=lambda n=i: self.activate_slot(n))
            button.pack(side='left')
            button.bind('<Button-3>', lambda event, n=i: self.load_slot(n))
            ttk.Button(line, text=tr('Laden'), width=6,
                       command=lambda n=i: self.load_slot(n)).pack(side='left', padx=(4,0))
            self.profile_buttons.append(button)
        player = ttk.LabelFrame(profile_row, text=tr('MIDI-bestand'), padding=2)
        player.pack(side='left', fill='both', padx=(3,0))
        for i,(label,command) in enumerate((('Open',self.open_midi_file),('▶ Play',self.play_midi_file),(tr('Pauze'),self.pause_midi_file),('■ Stop',self.stop_midi_file))):
            ttk.Button(player,text=label,command=command,width=7).grid(row=i//2,column=i%2,sticky='ew',padx=1,pady=1)
        ttk.Label(player,textvariable=self.midi_title,wraplength=125).grid(row=2,column=0,columnspan=2,sticky='w')
        midi = ttk.LabelFrame(right, text=tr('MIDI-invoer'), padding=2)
        midi.pack(fill='x')
        self.combo = ttk.Combobox(midi, state='readonly', textvariable=self.device_name, width=17)
        self.combo.pack(side='left', fill='x', expand=True)
        ttk.Button(midi, text=tr('Vernieuwen'), command=self.refresh_devices).pack(side='left', padx=(0, 5))
        ttk.Button(midi, text=tr('Verbinden'), command=self.connect_midi).pack(side='left')
        top = ttk.Frame(left)
        top.pack(fill='x')
        ttk.Button(top, text=tr('■ Alle noten uit'), command=self.all_off).pack(side='left', padx=(0, 16))
        top = ttk.Frame(left); top.pack(fill='x')
        ttk.Label(top, text='Volume').pack(side='left')
        ttk.Scale(top, from_=0, to=70, variable=self.volume, command=self.update_volume, length=65).pack(side='left', padx=6)
        ttk.Label(top, text=tr('Max. cent')).pack(side='left', padx=(8, 4))
        ttk.Combobox(top, state='readonly', width=4, values=['15', '30', '50', '100'], textvariable=self.range_max).pack(side='left')
        self.range_max.trace_add('write', lambda *_: self.redraw())
        sound = ttk.LabelFrame(editor, text=tr('Klankbron'), padding=2)
        sound.pack(fill='x', pady=0)
        ttk.Radiobutton(sound, text=tr('Sinus + drawbars'), variable=self.sound_mode, value='sinus', command=self.change_sound).pack(side='left', padx=(0, 3))
        ttk.Radiobutton(sound, text=tr('Accordeon'), variable=self.sound_mode, value='accordion', command=self.change_sound).pack(side='left', padx=(0, 3))
        harmonics = ttk.LabelFrame(editor, text=tr('Drawbars (sinusklank)'), padding=2)
        harmonics.pack(fill='x', pady=(0, 3))
        bar = ttk.Frame(harmonics)
        bar.pack(fill='x')
        for i, (label, var) in enumerate(zip(('2×', '3×', '4×', '5×'), self.drawbar_vars)):
            section = ttk.Frame(bar)
            section.grid(row=0,column=i,sticky='ew',padx=2)
            bar.columnconfigure(i,weight=1)
            ttk.Label(section, text=label).pack(anchor='w')
            line = ttk.Frame(section)
            line.pack(fill='x')
            ttk.Scale(line, from_=0, to=100, variable=var,
                      length=40, command=self.update_harmonics).pack(side='left', fill='x', expand=True)
            readout = ttk.Label(line, text='0%', width=5)
            readout.pack(side='bottom')
            var.trace_add('write', lambda *_, v=var, w=readout: w.config(text=f'{v.get():.0f}%'))
            readout.config(text=f'{var.get():.0f}%')
        ttk.Button(bar, text=tr('Alleen sinus'), command=self.reset_harmonics).grid(row=1,column=0,columnspan=4,sticky='e')
        tuning = ttk.LabelFrame(editor, text=tr('Registers en referentie'), padding=4)
        tuning.pack(fill='x')
        line = ttk.Frame(tuning); line.pack(fill='x')
        ttk.Label(line,text='A4 (Hz)').pack(side='left')
        ref = ttk.Entry(line,textvariable=self.ref_var,width=8); ref.pack(side='left',padx=4)
        ref.bind('<Return>',lambda e:self.apply_reference())
        ttk.Button(line,text=tr('Instellen'),command=self.apply_reference).pack(side='left')
        ttk.Checkbutton(line,text=tr('Driekorige modus'),variable=self.extended,command=self.change_registers).pack(side='left',padx=2)
        line = ttk.Frame(tuning); line.pack(fill='x')
        self.register_frames = []
        for k,name in enumerate(('M−','M','M+')):
            frame = ttk.Frame(line); frame.pack(side='left',padx=5)
            ttk.Checkbutton(frame,text=name,variable=self.enabled[k],command=self.change_registers).pack(side='left')
            ttk.Scale(frame,from_=0,to=100,variable=self.levels[k],length=42,command=self.change_registers).pack(side='left')
            self.register_frames.append(frame)
        self.extra = ttk.Frame(left)
        ttk.Label(self.extra,text=tr('Bewerk curve:')).pack(side='left')
        for name in ('M−','M+'):
            ttk.Radiobutton(self.extra,text=name,value=name,variable=self.edit_register,command=self.refresh_edit).pack(side='left')
        extra_buttons = ttk.Frame(self.extra); extra_buttons.pack(side='bottom',fill='x')
        ttk.Button(extra_buttons,text=tr('Kopieer'),command=lambda:self.copy_curve(False)).pack(side='left',padx=5)
        ttk.Button(extra_buttons,text=tr('Spiegel'),command=lambda:self.copy_curve(True)).pack(side='left')
        edit = ttk.Frame(left); edit.pack(fill='x',pady=2)
        self.selected_label = ttk.Label(edit,width=6,font=('Segoe UI',11,'bold')); self.selected_label.pack(side='left')
        self.freq_label = ttk.Label(edit,width=17); self.freq_label.pack(side='left')
        edit = ttk.Frame(left); edit.pack(fill='x')
        ttk.Label(edit,text='Cents').pack(side='left')
        self.cent_entry = ttk.Entry(edit,textvariable=self.selected_value,width=7); self.cent_entry.pack(side='left',padx=4)
        ttk.Label(edit,text='Δ Hz').pack(side='left')
        self.hz_entry = ttk.Entry(edit,textvariable=self.hz_value,width=8); self.hz_entry.pack(side='left',padx=4)
        for entry,unit in ((self.cent_entry,'cents'),(self.hz_entry,'hz')):
            entry.bind('<FocusIn>',self.on_entry_focus)
            entry.bind('<Return>',lambda e,u=unit:self.apply_exact(u))
            for key,delta in (('Right',1),('Left',-1),('KP_6',1),('KP_4',-1)):
                entry.bind('<'+key+'>',lambda e,d=delta:self.move_selection(d))
        self.selected_value.trace_add('write',lambda *_:self.auto_apply_entry('cents'))
        self.hz_value.trace_add('write',lambda *_:self.auto_apply_entry('hz'))
        self.beat_label = ttk.Label(left,wraplength=285); self.beat_label.pack(anchor='w')
        ttk.Checkbutton(left,text=tr('Toon zweving (Hz)'),variable=self.show_hz,command=self.redraw).pack(anchor='w')
        self.last_unit = 'cents'
        self.change_registers()
        files = ttk.Frame(right)
        files.pack(fill='x', pady=0)
        ttk.Button(files, text=tr('Opslaan...'), command=self.save).pack(side='left', padx=(0, 6))
        ttk.Button(files, text=tr('Laden...'), command=self.load).pack(side='left')
        ttk.Button(files, text=tr('Profiel bijwerken'),
                   command=self.save_active_slot).pack(side='left', padx=(3, 0))
        self.legend = ttk.Frame(outer); self.legend.pack(fill='x')
        self.canvas = tk.Canvas(outer, bg='#ffffff', highlightthickness=1, highlightbackground='#b7c3ce', height=180, cursor='crosshair')
        self.canvas.pack(fill='both', expand=True, pady=(4, 6))
        self.canvas.bind('<Configure>', lambda e: self.redraw())
        self.canvas.bind('<ButtonPress-1>', self.on_down)
        self.canvas.bind('<B1-Motion>', self.on_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_up)
        test = ttk.LabelFrame(outer, text=tr('Testtonen (ingedrukt houden)'), padding=2)
        test.pack(fill='x', pady=(0, 2))
        self.test_panel = test
        self.root.bind('<F11>', self.toggle_controls)
        keys = ttk.Frame(test)
        keys.pack(anchor='w')
        for note in range(60, 73):
            b = tk.Button(keys, text=note_name(note), width=4, padx=1, pady=0)
            b.pack(side='left', padx=2)
            b.bind('<ButtonPress-1>', lambda e, n=note: self.test_on(n))
            b.bind('<ButtonRelease-1>', lambda e, n=note: self.test_off(n))
        ttk.Label(outer, textvariable=self.status, foreground='#225e80').pack(anchor='w')
        self.sync_selected()

    def switch_language(self):
        global LANG
        old = LANG
        LANG = 'nl' if LANG == 'en' else 'en'
        reverse = {v:k for k,v in TRANSLATIONS.items()}
        def visit(widget):
            try:
                value = widget.cget('text')
                if value:
                    key = reverse.get(value, value) if old == 'en' else value
                    if key in TRANSLATIONS: widget.configure(text=tr(key))
            except tk.TclError:
                pass
            for child in widget.winfo_children(): visit(child)
        visit(self.root)
        self.root.title(tr('Accordeon Zwevingslab — versie 3.4'))
        self.update_profile_buttons()
        self.sync_selected()
        self.redraw()
        self.status.set(tr('Kies een testtoon of verbind MIDI.'))
        if not self.midi_events: self.midi_title.set(tr('Geen MIDI-bestand'))
        try:
            PREF.parent.mkdir(parents=True, exist_ok=True)
            PREF.write_text(json.dumps({'language':LANG}), encoding='utf-8')
        except OSError:
            pass

    def toggle_controls(self, event=None):
        if self.controls.winfo_manager():
            self.controls.pack_forget(); self.test_panel.pack_forget()
        else:
            self.controls.pack(fill='x',before=self.legend,pady=(0,3))
            self.test_panel.pack(fill='x',after=self.canvas)
        return 'break'

    @staticmethod
    def pair_color(name):
        return {'M/M+':'#d73535','M−/M':'#a53e90','M−/M+':'#956222'}[name]

    def update_legend(self, curves, pairs):
        items=[(name+' (cent)',color) for _,color,name in curves]+[(name+' (Hz)',self.pair_color(name)) for name,_ in pairs]
        if getattr(self,'legend_items',None)==items: return
        self.legend_items=items
        for child in self.legend.winfo_children(): child.destroy()
        for name,color in items:
            ttk.Label(self.legend,text='━ '+name,foreground=color).pack(side='left',padx=6)

    def change_sound(self):
        self.audio.set_mode(self.sound_mode.get())
        self.midi_held.clear()
        self.test_notes.clear()
        self.redraw()
        self.status.set(tr('Klankbron: ') + (tr('Accordeon (9 meetnoten)') if
                        self.sound_mode.get() == 'accordion' else tr('Sinus + drawbars')))

    def save_active_slot(self):
        if self.active_slot is None or self.profile_slots[self.active_slot] is None:
            messagebox.showinfo(tr('Profiel opslaan'),
                tr('Kies eerst een van de drie profielvakken.\nAls je het profiel al hebt bewerkt, gebruik dan Profiel opslaan...'))
            return
        index = self.active_slot
        path = self.profile_slots[index]['path']
        if not messagebox.askyesno(tr('Profiel bijwerken'),
                                   (f'Save changes to:\n{path}?' if LANG == "en" else f'Wijzigingen opslaan in:\n{path}?')):
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profile_data(), f, indent=2)
            self.profile_slots[index]['values'] = self.profile_data()
            self.status.set((f'Profile {index+1} saved: {Path(path).name}' if LANG == "en" else f'Profiel {index+1} opgeslagen: {Path(path).name}'))
        except Exception as exc:
            messagebox.showerror(tr('Opslaan mislukt'), str(exc))

    def update_profile_buttons(self):
        for i, button in enumerate(self.profile_buttons):
            slot = self.profile_slots[i]
            name = Path(slot['path']).stem if slot else tr('(leeg)')
            button.config(text=f'{i+1}: {name[:17]}',
                          bg='#b9dfba' if i == self.active_slot else '#eeeeee',
                          relief='sunken' if i == self.active_slot else 'raised')

    def load_slot(self, index):
        path = filedialog.askopenfilename(initialdir=str(PROFILE_DIR), title=(f'Load profile {index+1}' if LANG == "en" else f'Profiel {index+1} laden'),
                                          filetypes=[(tr('Zwevingsprofiel'), '*.json')])
        if not path:
            return
        try:
            vals = self.read_profile(path)
            self.profile_slots[index] = {'path': path, 'values': vals}
            self.activate_slot(index)
        except Exception as exc:
            messagebox.showerror(tr('Profiel laden mislukt'), str(exc))

    def activate_slot(self, index):
        slot = self.profile_slots[index]
        if slot is None:
            self.load_slot(index)
            return
        self.active_slot = index
        self.install_profile(slot['values'])
        self.sync_selected()
        self.redraw()
        self.update_profile_buttons()
        self.status.set((f'Profile {index+1} active: {Path(slot["path"]).name}' if LANG == "en" else f'Profiel {index+1} actief: {Path(slot["path"]).name}'))

    @staticmethod
    def read_profile(path):
        with open(path,encoding='utf-8') as f: data=json.load(f)
        if data.get('low_midi')!=LOW or data.get('high_midi')!=HIGH: raise ValueError(tr('Onjuist notenbereik'))
        for key in ('cents','lower_cents'):
            vals=[float(v) for v in data.get(key,[0.]*(HIGH-LOW+1))]
            if len(vals)!=HIGH-LOW+1 or any(not math.isfinite(v) or abs(v)>100 for v in vals): raise ValueError(tr('Ongeldige centwaarden'))
            data[key]=vals
        ref=float(data.get('reference_hz',440))
        if not 400<=ref<=480: raise ValueError(tr('Referentie buiten 400–480 Hz'))
        levels=[float(v) for v in data.get('levels',[100]*3)]
        enabled=data.get('enabled',[True]*3)
        if len(levels)!=3 or any(not 0<=v<=100 for v in levels) or len(enabled)!=3: raise ValueError(tr('Ongeldige registerinstellingen'))
        data.update(reference_hz=ref,levels=levels,enabled=enabled)
        return data

    def open_midi_file(self):
        if mido is None:
            messagebox.showerror('MIDI', tr('Installeer mido: py -3.12 -m pip install mido'))
            return
        path = filedialog.askopenfilename(filetypes=[(tr('MIDI-bestanden'), '*.mid *.midi')])
        if not path:
            return
        try:
            mf = mido.MidiFile(path)
            # mido speelt tempo- en spoorinformatie samen in tijdvolgorde af.
            # Dit is een interne speler: er wordt geen MIDI-uitvoer geopend.
            t = 0.
            events = []
            for msg in mf:
                t += msg.time
                if msg.type in ('note_on', 'note_off') and msg.channel != 9:
                    if LOW <= msg.note <= HIGH:
                        events.append((t, msg.type, msg.note, msg.velocity))
                elif msg.type == 'control_change' and msg.control in (120, 123):
                    events.append((t, 'all_off', 0, 0))
            self.stop_midi_file()
            self.midi_events = events
            self.midi_index = 0
            self.midi_title.set(Path(path).name + (f'  ({len(events)} events)' if LANG == "en" else f'  ({len(events)} gebeurtenissen)'))
            self.status.set(tr('MIDI geladen. Klik op Play.'))
        except Exception as exc:
            messagebox.showerror(tr('MIDI laden mislukt'), str(exc))

    def play_midi_file(self):
        if not self.midi_events:
            self.open_midi_file()
            if not self.midi_events:
                return
        if self.midi_playing:
            return
        if self.audio.stream is None:
            self.start_audio()
            if self.audio.stream is None:
                return
        import time
        if self.midi_index >= len(self.midi_events):
            self.midi_index = 0
            self.midi_position = 0.
        self.midi_started = time.perf_counter() - self.midi_position
        self.midi_playing = True
        self.midi_paused = False

    def pause_midi_file(self):
        import time
        if self.midi_playing:
            self.midi_position = time.perf_counter() - self.midi_started
            self.midi_playing = False
            self.midi_paused = True
            for note in list(self.midi_notes):
                self.audio.note_off(note)
            self.midi_notes.clear()
            self.midi_held.clear()
            self.redraw()
        elif self.midi_paused:
            self.play_midi_file()

    def stop_midi_file(self):
        self.midi_playing = False
        self.midi_paused = False
        self.midi_index = 0
        self.midi_position = 0.
        for note in list(self.midi_notes):
            self.audio.note_off(note)
        self.midi_notes.clear()
        self.midi_held.clear()
        if hasattr(self, 'canvas'):
            self.redraw()

    def poll_file_player(self):
        if self.midi_playing:
            import time
            elapsed = time.perf_counter() - self.midi_started
            changed = False
            while (self.midi_index < len(self.midi_events) and
                   self.midi_events[self.midi_index][0] <= elapsed):
                _, kind, note, velocity = self.midi_events[self.midi_index]
                if kind == 'note_on' and velocity > 0:
                    self.audio.note_on(note, velocity)
                    self.midi_notes.add(note)
                    self.midi_held.add(note)
                elif kind in ('note_off', 'note_on'):
                    self.audio.note_off(note)
                    self.midi_notes.discard(note)
                    self.midi_held.discard(note)
                elif kind == 'all_off':
                    for n in list(self.midi_notes):
                        self.audio.note_off(n)
                    self.midi_notes.clear()
                    self.midi_held.clear()
                changed = True
                self.midi_index += 1
            if changed:
                self.redraw()
            if self.midi_index >= len(self.midi_events):
                self.stop_midi_file()
        self.root.after(10, self.poll_file_player)

    def bounds(self):
        w = max(self.canvas.winfo_width(), 150)
        h = max(self.canvas.winfo_height(), 80)
        return 56, 18, w-58, h-40

    def coord(self, idx, cents):
        l,t,r,b = self.bounds()
        maximum = self.range_max.get()
        minimum = -maximum if self.extended.get() or min(self.values)<0 else 0.
        return l+idx/(HIGH-LOW)*(r-l), b-(cents-minimum)/(maximum-minimum)*(b-t)

    def from_xy(self,x,y):
        l,t,r,b = self.bounds()
        m = self.range_max.get(); low = -m if self.extended.get() or min(self.values)<0 else 0.
        return max(0,min(HIGH-LOW,round((x-l)/(r-l)*(HIGH-LOW)))), round(max(low,min(m,low+(b-y)/(b-t)*(m-low))),2)

    def redraw(self):
        if not hasattr(self,'canvas'): return
        c=self.canvas; c.delete('all'); l,t,r,b=self.bounds()
        m=self.range_max.get(); low=-m if self.extended.get() or min(self.values)<0 else 0.
        for v in np.linspace(low,m,7):
            y=self.coord(0,v)[1]; c.create_line(l,y,r,y,fill='#e2e9ef'); c.create_text(l-8,y,text=f'{v:g}',anchor='e')
        for n in range(LOW,HIGH+1,12):
            x=self.coord(n-LOW,0)[0]; c.create_line(x,t,x,b,fill='#e2e9ef'); c.create_text(x,b+19,text=note_name(n))
        c.create_text(12,9,text='cents',anchor='w')
        curves=[(self.values,'#087ec1','M+')]
        if self.extended.get(): curves.append((self.lower,'#d97732','M−'))
        for vals,color,name in curves:
            pts=[z for i,v in enumerate(vals) for z in self.coord(i,v)]
            c.create_line(*pts,fill=color,width=3 if name==self.edit_register.get() else 2)
        y=self.coord(0,0)[1]; c.create_line(l,y,r,y,fill='#777777',dash=(4,3))
        pairs=self.beat_curves() if self.show_hz.get() else [];  hzmax=max([1.]+[max(v)*1.08 for _,v in pairs])
        for j,(name,vals) in enumerate(pairs):
            pts=[z for i,v in enumerate(vals) for z in (l+i/(HIGH-LOW)*(r-l),b-v/hzmax*(b-t))]
            c.create_line(*pts,fill=self.pair_color(name),width=2,dash=() if j==0 else (4,3))
        for v in (np.linspace(0,hzmax,6) if pairs else []): c.create_text(r+5,b-v/hzmax*(b-t),text=f'{v:.1f}',anchor='w',fill='#c22b2b')
        if pairs: c.create_text(r+5,t-9,text='Hz',anchor='w',fill='#c22b2b')
        self.update_legend(curves,pairs)
        x=self.coord(self.selected-LOW,0)[0]; c.create_line(x,t,x,b,fill='#f0a642',dash=(3,4))
        vals=self.edit_values()
        for n in sorted(self.midi_held|self.test_notes|{self.selected}):
            if LOW<=n<=HIGH:
                x,y=self.coord(n-LOW,vals[n-LOW]); c.create_oval(x-5,y-5,x+5,y+5,fill='#d72668' if n!=self.selected else '#ef9c36')

    def sync_selected(self):
        if not hasattr(self,'freq_label'): return
        f=self.base_frequency(); v=self.edit_values()[self.selected-LOW]
        self.selected_label.config(text=note_name(self.selected))
        self.freq_label.config(text=f'M: {f:.3f} Hz')
        self._syncing_entry=True
        try:
            self.selected_value.set(f'{v:.2f}'); self.hz_value.set(f'{f*math.expm1(v*math.log(2)/1200):.3f}')
        finally: self._syncing_entry=False
        self.beat_label.config(text=tr('Zweving: ')+ '   |   '.join(f'{name}: {vals[self.selected-LOW]:.3f} Hz' for name,vals in self.beat_curves()))

    def on_entry_focus(self,event):
        self.last_unit='hz' if event.widget==self.hz_entry else 'cents'
        event.widget.selection_range(0,'end')

    def move_selection(self,delta):
        self.selected=max(LOW,min(HIGH,self.selected+delta)); self.sync_selected(); self.redraw()
        entry=self.hz_entry if self.last_unit=='hz' else self.cent_entry
        entry.focus_set(); entry.selection_range(0,'end'); return 'break'

    def auto_apply_entry(self,unit):
        if self._syncing_entry: return
        self.last_unit=unit
        text=(self.hz_value if unit=='hz' else self.selected_value).get().strip()
        digits=3 if unit=='hz' else 2
        if re.fullmatch(r'[+-]?\d+[.,]\d{'+str(digits)+'}',text): self.apply_exact(unit,quiet=True)

    def set_point(self, idx, cents):
        self.edit_values()[idx] = cents
        self.update_profile_buttons()
        self.selected = LOW+idx
        self.push_audio()
        self.sync_selected()
        self.redraw()

    def on_down(self, event):
        idx, cents = self.from_xy(event.x, event.y)
        self.dragging = True
        self.last_drag = (idx, cents)
        self.set_point(idx, cents)

    def on_drag(self, event):
        if not self.dragging:
            return
        idx, cents = self.from_xy(event.x, event.y)
        old_i, old_v = self.last_drag
        if idx != old_i:
            for i in range(min(old_i, idx), max(old_i, idx)+1):
                frac = (i-old_i)/(idx-old_i)
                self.edit_values()[i] = round(old_v + frac*(cents-old_v), 2)
        self.last_drag = (idx, cents)
        self.set_point(idx, cents)

    def on_up(self, event):
        self.dragging = False
        self.last_drag = None

    def apply_exact(self,unit='cents',quiet=False):
        try:
            v=float((self.hz_value if unit=='hz' else self.selected_value).get().replace(',','.'))
            if unit=='hz': v=1200*math.log2(1+v/self.base_frequency())
            if not math.isfinite(v) or abs(v)>100: raise ValueError()
        except ValueError:
            if not quiet: messagebox.showerror(tr('Ongeldige waarde'),tr('Gebruik een afwijking binnen ±100 cents.'))
            return
        self.set_point(self.selected-LOW,v)
        self.fit_range(); self.redraw()
        (self.hz_entry if unit=='hz' else self.cent_entry).selection_range(0,'end')

    def flat(self):
        self.edit_values()[:]=[0.]*(HIGH-LOW+1); self.refresh_edit()

    def example(self):
        sign=-1 if self.edit_register.get()=='M−' else 1
        self.edit_values()[:]=[sign*round(2+10*(i/(HIGH-LOW))**1.15,2) for i in range(HIGH-LOW+1)]; self.refresh_edit()

    def update_harmonics(self, *_):
        self.audio.set_harmonics([v.get() for v in self.drawbar_vars])

    def reset_harmonics(self):
        for v in self.drawbar_vars:
            v.set(0)
        self.update_harmonics()

    def update_volume(self, *_):
        self.audio.volume = self.volume.get()/100

    def start_audio(self):
        try:
            self.audio.start()
            self.status.set(tr('Audio actief. Speel via MIDI of met de testknoppen.'))
        except Exception as exc:
            messagebox.showerror(tr('Audiofout'), (f'Audio start failed:\n{exc}' if LANG == "en" else f'Audio starten mislukt:\n{exc}'))

    def test_on(self, note):
        if self.audio.stream is None:
            self.start_audio()
        if self.audio.stream is not None:
            self.test_notes.add(note)
            self.audio.note_on(note)
            self.redraw()

    def test_off(self, note):
        self.test_notes.discard(note)
        self.audio.note_off(note)
        self.redraw()

    def all_off(self):
        self.audio.all_off()
        self.test_notes.clear()
        self.midi_held.clear()
        self.redraw()

    def refresh_devices(self):
        if mido is None:
            self.status.set(tr('MIDI niet beschikbaar: installeer mido en python-rtmidi.'))
            self.midi_devices = []
        else:
            try:
                self.midi_devices = mido.get_input_names()
            except Exception as exc:
                self.midi_devices = []
                self.status.set((f'MIDI ports unavailable: {exc}' if LANG == "en" else f'MIDI-poorten niet beschikbaar: {exc}'))
        self.combo['values'] = self.midi_devices
        if self.midi_devices and self.device_name.get() not in self.midi_devices:
            self.device_name.set(self.midi_devices[0])

    def connect_midi(self):
        if mido is None:
            messagebox.showinfo('MIDI', tr('Installeer: py -3.12 -m pip install mido python-rtmidi'))
            return
        name = self.device_name.get()
        if not name:
            messagebox.showinfo('MIDI', tr('Er is geen MIDI-ingang geselecteerd.'))
            return
        try:
            if self.midi_port is not None:
                self.midi_port.close()
            self.midi_port = mido.open_input(name, callback=lambda msg: self.midi_queue.put(msg))
            self.status.set((f'MIDI connected: {name}' if LANG == "en" else f'MIDI verbonden: {name}'))
            if self.audio.stream is None:
                self.start_audio()
        except Exception as exc:
            self.midi_port = None
            messagebox.showerror(tr('MIDI-fout'), str(exc))

    def poll_midi(self):
        changed = False
        try:
            for _ in range(200):
                msg = self.midi_queue.get_nowait()
                if msg.type == 'note_on' and msg.velocity > 0:
                    self.audio.note_on(msg.note, msg.velocity)
                    self.midi_held.add(msg.note)
                    changed = True
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    self.audio.note_off(msg.note)
                    self.midi_held.discard(msg.note)
                    changed = True
                elif msg.type == 'control_change' and msg.control in (120, 123):
                    self.audio.all_off()
                    self.midi_held.clear()
                    changed = True
        except queue.Empty:
            pass
        if changed:
            self.redraw()
        self.root.after(25, self.poll_midi)

    def save(self):
        path = filedialog.asksaveasfilename(title=tr('Profiel opslaan'), defaultextension='.json',
                                            filetypes=[(tr('Zwevingsprofiel'), '*.json')])
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.profile_data(), f, indent=2)
            self.status.set((f'Profile saved: {path}' if LANG == "en" else f'Profiel opgeslagen: {path}'))
        except Exception as exc:
            messagebox.showerror(tr('Opslaan mislukt'), str(exc))

    def load(self):
        path = filedialog.askopenfilename(initialdir=str(PROFILE_DIR), title=tr('Profiel laden'), filetypes=[(tr('Zwevingsprofiel'), '*.json')])
        if not path:
            return
        try:
            vals = self.read_profile(path)
            self.install_profile(vals)
            self.active_slot = None
            self.update_profile_buttons()
            self.sync_selected()
            self.redraw()
            self.status.set((f'Profile loaded: {path}' if LANG == "en" else f'Profiel geladen: {path}'))
        except Exception as exc:
            messagebox.showerror(tr('Laden mislukt'), str(exc))

    def base_frequency(self):
        return self.reference*2**((self.selected-69)/12)

    def edit_values(self):
        return self.lower if self.edit_register.get()=='M−' else self.values

    def push_audio(self):
        gains=[v.get()/100 if e.get() else 0. for v,e in zip(self.levels,self.enabled)]
        if not self.extended.get(): gains[0]=0.
        self.audio.set_profile(self.values,self.lower,self.reference,gains)

    def change_registers(self,*_):
        if self.extended.get():
            self.register_frames[0].pack(side='left',before=self.register_frames[1],padx=5)
            self.extra.pack(fill='x')
        else:
            self.register_frames[0].pack_forget(); self.extra.pack_forget(); self.edit_register.set('M+')
        self.refresh_edit()

    def refresh_edit(self):
        self.push_audio(); self.fit_range(); self.sync_selected(); self.redraw()

    def fit_range(self):
        m=max(abs(v) for v in self.values+(self.lower if self.extended.get() else []))
        if m>self.range_max.get(): self.range_max.set(next((x for x in (15,30,50,100) if x>=m),100))

    def apply_reference(self):
        try:
            v=float(self.ref_var.get().replace(',','.'))
            if not 400<=v<=480: raise ValueError()
        except ValueError:
            messagebox.showerror(tr('Referentie'),tr('Gebruik 400–480 Hz')); return
        self.reference=v; self.reference_initialized=True; self.refresh_edit()

    def copy_curve(self,mirror):
        other=self.values if self.edit_register.get()=='M−' else self.lower
        other[:]=[(-v if mirror else v) for v in self.edit_values()]; self.refresh_edit()

    def beat_curves(self):
        f=self.reference*np.exp2((np.arange(LOW,HIGH+1)-69)/12)
        a=f*np.exp2(np.array(self.lower)/1200); b=f*np.exp2(np.array(self.values)/1200)
        active=[e.get() and v.get()>0 for e,v in zip(self.enabled,self.levels)]
        active[0]=active[0] and self.extended.get()
        pairs=[]
        for i,j,name,vals in [(1,2,'M/M+',abs(b-f)),(0,1,'M−/M',abs(a-f)),(0,2,'M−/M+',abs(b-a))]:
            if active[i] and active[j]: pairs.append((name,vals))
        return pairs

    def profile_data(self):
        return dict(format='Accordeon Zwevingslab v2',low_midi=LOW,high_midi=HIGH,cents=list(self.values),lower_cents=list(self.lower),reference_hz=self.reference,extended=self.extended.get(),enabled=[v.get() for v in self.enabled],levels=[v.get() for v in self.levels])

    def install_profile(self,data):
        self.values=list(data['cents']); self.lower=list(data['lower_cents'])
        if not self.reference_initialized:
            self.reference=data['reference_hz']
            self.reference_initialized=True
        self.ref_var.set(f'{self.reference:.2f}')
        self.extended.set(bool(data.get('extended',False)))
        for var,v in zip(self.enabled,data['enabled']): var.set(bool(v))
        for var,v in zip(self.levels,data['levels']): var.set(v)
        self.change_registers()

    def close(self):
        try:
            if self.midi_port is not None:
                self.midi_port.close()
            self.stop_midi_file()
            self.audio.stop()
        finally:
            self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    App(root)
    root.mainloop()
