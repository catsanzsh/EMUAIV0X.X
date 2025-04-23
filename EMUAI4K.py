import tkinter as tk
from PIL import Image, ImageTk
import sys
import numpy as np

class Memory:
    def __init__(self, prg_rom):
        self.ram = [0] * 0x800  # 2KB RAM
        self.prg_rom = prg_rom  # Program ROM

    def read(self, address):
        if address < 0x2000:
            return self.ram[address % 0x800]  # RAM mirroring
        elif address >= 0x8000:
            return self.prg_rom[(address - 0x8000) % len(self.prg_rom)]  # ROM
        return 0

    def write(self, address, value):
        if address < 0x2000:
            self.ram[address % 0x800] = value & 0xFF

    def read_word(self, address):
        lo = self.read(address)
        hi = self.read(address + 1)
        return (hi << 8) | lo

class CPU:
    def __init__(self, memory):
        self.memory = memory
        self.PC = self.memory.read_word(0xFFFC)
        self.A = 0  # Accumulator
        self.X = 0  # X register
        self.Y = 0  # Y register
        self.SP = 0xFD  # Stack Pointer
        self.status = 0x24  # Processor status (IRQ disabled)

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

        # Only a few opcodes for demo: LDA (immediate), STA (absolute), JMP (absolute), NOP, BRK
        if opcode == 0xA9:  # LDA immediate
            value = self.memory.read(self.PC)
            self.PC = (self.PC + 1) & 0xFFFF
            self.A = value
            self.set_flag(0x02, self.A == 0)  # Zero flag
            self.set_flag(0x80, self.A & 0x80)  # Negative flag
        elif opcode == 0x8D:  # STA absolute
            lo = self.memory.read(self.PC)
            hi = self.memory.read(self.PC + 1)
            addr = lo | (hi << 8)
            self.PC = (self.PC + 2) & 0xFFFF
            self.memory.write(addr, self.A)
        elif opcode == 0x4C:  # JMP absolute
            lo = self.memory.read(self.PC)
            hi = self.memory.read(self.PC + 1)
            self.PC = lo | (hi << 8)
        elif opcode == 0xEA:  # NOP
            pass
        elif opcode == 0x00:  # BRK
            pass  # For now, do nothing
        else:
            # Unimplemented opcode: treat as NOP
            pass

class PPU:
    def __init__(self, chr_rom):
        self.chr_rom = chr_rom
        self.frame = np.zeros((240, 256, 3), dtype=np.uint8)

    def render_frame(self):
        # Return a numpy array for efficiency
        self.frame.fill(0)  # Black screen
        return self.frame

class EmulatorApp:
    def __init__(self, root, rom_file):
        self.root = root
        self.root.title("NES Emulator")

        self.canvas = tk.Canvas(root, width=512, height=480)
        self.canvas.pack(pady=10)

        self.image = Image.new("RGB", (256, 240))
        self.tk_image = ImageTk.PhotoImage(self.image)
        self.img_on_canvas = self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)
        self.canvas.scale("all", 0, 0, 2, 2)

        try:
            with open(rom_file, 'rb') as f:
                header = f.read(16)
                prg_rom_size = 16384 * header[4]
                chr_rom_size = 8192 * header[5]
                prg_rom = f.read(prg_rom_size)
                chr_rom = f.read(chr_rom_size)
        except FileNotFoundError:
            print(f"Error: ROM file '{rom_file}' not found.")
            sys.exit(1)

        self.memory = Memory(prg_rom)
        self.cpu = CPU(self.memory)
        self.ppu = PPU(chr_rom)
        self.running = False

    def start(self):
        self.running = True
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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python EMUAINES.py <rom_file>")
        sys.exit(1)
    rom_file = sys.argv[1]
    root = tk.Tk()
    app = EmulatorApp(root, rom_file)
    app.start()
    root.mainloop()
