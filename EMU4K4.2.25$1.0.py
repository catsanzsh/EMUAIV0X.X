import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import os # Add os import if not already present

# --- NES Constants ---
RAM_SIZE = 0x800  # 2KB internal RAM
SCREEN_WIDTH, SCREEN_HEIGHT = 256, 240

# --- Memory Map ---
class Memory:
    def __init__(self, prg_rom):
        self.ram = [0] * RAM_SIZE
        self.prg_rom = prg_rom

    def read(self, address):
        if address < 0x2000:
            return self.ram[address % RAM_SIZE]
        elif address >= 0x8000:
            return self.prg_rom[(address - 0x8000) % len(self.prg_rom)]
        return 0

    def write(self, address, value):
        if address < 0x2000:
            self.ram[address % RAM_SIZE] = value & 0xFF

    def read_word(self, address):
        lo = self.read(address)
        hi = self.read((address + 1) & 0xFFFF)
        return (hi << 8) | lo

# --- CPU Skeleton (6502 Subset) ---
class CPU:
    def __init__(self, memory):
        self.memory = memory
        self.PC = self.memory.read_word(0xFFFC)
        self.A = 0
        self.X = 0
        self.Y = 0
        self.SP = 0xFD
        self.status = 0x24  # IRQ disabled

    def set_flag(self, flag, value):
        if value:
            self.status |= flag
        else:
            self.status &= ~flag

    def get_flag(self, flag):
        return (self.status & flag) != 0

    def step(self):
        opcode = self.memory.read(self.PC)
        self.PC = (self.PC + 1) & 0xFFFF

        if opcode == 0xA9:  # LDA immediate
            value = self.memory.read(self.PC)
            self.PC = (self.PC + 1) & 0xFFFF
            self.A = value
            self.set_flag(0x02, self.A == 0)  # Zero
            self.set_flag(0x80, self.A & 0x80)  # Negative
        elif opcode == 0x8D:  # STA absolute
            lo = self.memory.read(self.PC)
            hi = self.memory.read((self.PC + 1) & 0xFFFF)
            addr = lo | (hi << 8)
            self.PC = (self.PC + 2) & 0xFFFF
            self.memory.write(addr, self.A)
        elif opcode == 0x4C:  # JMP absolute
            lo = self.memory.read(self.PC)
            hi = self.memory.read((self.PC + 1) & 0xFFFF)
            self.PC = lo | (hi << 8)
        elif opcode == 0xEA:  # NOP
            pass
        elif opcode == 0x00:  # BRK
            pass  # Not implemented
        else:
            pass  # Unimplemented opcode

# --- PPU Skeleton ---
class PPU:
    def __init__(self, chr_rom):
        self.chr_rom = chr_rom
        self.frame = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

    def render_frame(self):
        self.frame.fill(0)  # Black screen
        return self.frame

# --- iNES ROM Loader ---
def load_ines_rom(filename):
    with open(filename, 'rb') as f:
        header = f.read(16)
        if header[0:4] != b"NES\x1a":
            raise ValueError("Not a valid iNES ROM file.")

        prg_rom_size = header[4] * 16 * 1024
        chr_rom_size = header[5] * 8 * 1024

        # Skip trainer if present
        if header[6] & 0x04:
            f.read(512)

        prg_rom = f.read(prg_rom_size)
        chr_rom = f.read(chr_rom_size) if chr_rom_size > 0 else bytes()

        return prg_rom, chr_rom

# --- Emulator GUI (Nesticle-style) ---
class EmulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("NesticlePy - NES Emulator")
        self.root.configure(bg="#C0C0C0")  # Classic gray

        # Menu bar
        menubar = tk.Menu(root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Open ROM...", command=self.open_rom)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        root.config(menu=menubar)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("No ROM loaded.")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#E0E0E0")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Canvas for NES screen
        self.canvas = tk.Canvas(root, width=SCREEN_WIDTH * 2, height=SCREEN_HEIGHT * 2, bg="#000000", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(padx=10, pady=10)

        self.image = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT))
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.img_on_canvas = self.canvas.create_image(
            0, 0, image=self.tk_image, anchor=tk.NW
        )
        self.canvas.scale("all", 0, 0, 2, 2)

        # Emulator state
        self.memory = None
        self.cpu = None
        self.ppu = None
        self.running = False
        self.rom_cache = {} # Add a dictionary to cache loaded ROMs

    def open_rom(self):
        rom_file = filedialog.askopenfilename(
            title="Open NES ROM",
            filetypes=[("NES ROMs", "*.nes"), ("All files", "*.*")]
        )
        if not rom_file:
            return

        # Check cache first
        if rom_file in self.rom_cache:
            prg_rom, chr_rom = self.rom_cache[rom_file]
            print(f"Loading ROM from cache: {rom_file}") # Optional: Log cache hit
        else:
            # Load from file if not in cache
            try:
                prg_rom, chr_rom = load_ines_rom(rom_file)
                # Store in cache
                self.rom_cache[rom_file] = (prg_rom, chr_rom)
                print(f"Loaded ROM from file and cached: {rom_file}") # Optional: Log file load
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM:\n{e}")
                return

        # Reset and start emulation
        self.memory = Memory(prg_rom)
        self.cpu = CPU(self.memory)
        self.ppu = PPU(chr_rom)
        self.status_var.set(f"Loaded: {os.path.basename(rom_file)}") # Show only filename
        self.running = True
        # Ensure previous emulation loop stops if any
        # self.root.after_cancel(self.emulate_id) # You might need an ID like self.emulate_id = self.root.after(...)
        self.emulate()

    def emulate(self):
        if not self.running:
            return
        self.cpu.step()
        frame = self.ppu.render_frame()
        self.image = Image.fromarray(frame, 'RGB')
        self.tk_image.paste(self.image)
        self.canvas.itemconfig(self.img_on_canvas, image=self.tk_image)
        self.root.after(16, self.emulate)
        # Store the after ID if you need to cancel it later
        self.emulate_id = self.root.after(16, self.emulate)

# --- Main Entry Point ---
def main():
    root = tk.Tk()
    app = EmulatorApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
