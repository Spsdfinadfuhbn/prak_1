import os
import sys
import argparse
import tkinter as tk
from tkinter import scrolledtext

class ShellEmulatorGUI:
    """Графический интерфейс и REPL-обработчик ."""
    def __init__(self, root, vfs, prompt, script_path):
        self.root = root
        self.vfs = vfs
        self.prompt = prompt
        self.script_path = script_path

        self.root.title(f"Shell Emulator - VFS: {self.vfs.root_name}")
        self.root.geometry("800x500")

        self.text_area = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, bg="black", fg="white",
            insertbackground="white", font=("Courier", 12)
        )
        self.text_area.pack(fill=tk.BOTH, expand=True)
        self.text_area.bind("<Return>", self.handle_enter)
        self.text_area.bind("<Key>", self.restrict_cursor)

        self.insert_prompt()
        if self.script_path:
            self.root.after(100, self.run_start_script)

    def insert_prompt(self):
        """Выводит строку приглашения."""
        p_str = f"{self.prompt.replace('{dir}', self.vfs.current_dir)}"
        self.text_area.insert(tk.END, p_str)
        self.text_area.mark_set("input_start", "end-1c")
        self.text_area.see(tk.END)

    def restrict_cursor(self, event):
        """Запрещает изменять историю."""
        if self.text_area.compare("insert", "<", "input_start"):
            self.text_area.mark_set("insert", "end")

    def handle_enter(self, event):
        """Обработка нажатия Enter."""
        cmd_line = self.text_area.get("input_start", "end-1c").strip()
        self.text_area.insert(tk.END, "\n")
        if cmd_line:
            stop = self.execute_command(cmd_line)
            if stop:
                self.root.destroy()
                return "break"
        self.insert_prompt()
        return "break"

    def parse_arguments(self, cmd_line):
        """Раскрывает переменные окружения реальной ОС ."""
        expanded = os.path.expandvars(cmd_line)
        parts = expanded.split()
        return parts, parts[1:] if len(parts) > 1 else []

    def execute_command(self, cmd_line):
        """Маршрутизатор команд."""
        try:
            cmd, args = self.parse_arguments(cmd_line)
        except Exception:
            self.text_area.insert(tk.END, "shell: syntax error\n")
            return "error"

        cmd_map = {
            "exit": lambda a: True, "pwd": self._cmd_pwd,
            "ls": self._cmd_ls, "cd": self._cmd_cd,
            "tail": self._cmd_tail, "rmdir": self._cmd_rmdir,
            "mv": self._cmd_mv
        }
        if cmd in cmd_map:
            return cmd_map[cmd](args)
        self.text_area.insert(tk.END, f"{cmd}: command not found\n")
        return "error"


    def run_start_script(self):
        """Выполнение стартового скрипта с остановкой по ошибке (Этап 2)."""
        if not os.path.exists(self.script_path):
            self.text_area.insert(tk.END, f"Script error: {self.script_path} not found.\n")
            self.insert_prompt()
            return
        with open(self.script_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            self.text_area.insert(tk.END, line + "\n")
            result = self.execute_command(line)
            if result == "error":
                self.text_area.insert(tk.END, "Script aborted due to error\n")
                break
            elif result is True:
                self.root.destroy()
                return
        self.insert_prompt()


def main():
    parser = argparse.ArgumentParser(description="Shell Emulator Configuration")
    parser.add_argument("--vfs", required=True, help="Path to physical VFS root")
    parser.add_argument("--prompt", default="[user@vfs {dir}]$ ", help="Prompt string")
    parser.add_argument("--script", default=None, help="Startup script path")
    args = parser.parse_args()
    print("=== DEBUG STARTUP PARAMETERS ===")
    print(f"VFS Path: {args.vfs}\nPrompt Format: {args.prompt}\nScript: {args.script}")
    print("================================")
    vfs = VirtualFileSystem(args.vfs)
    root = tk.Tk()
    app = ShellEmulatorGUI(root, vfs, args.prompt, args.script)
    root.mainloop()


if __name__ == "__main__":
    main()