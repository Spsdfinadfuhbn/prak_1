import os
import sys
import argparse
import tkinter as tk
from tkinter import scrolledtext

class VirtualFileSystem:
    """Виртуальная файловая система в оперативной памяти (Этап 3)."""
    def __init__(self, root_dir_path):
        self.fs = {}  # {'/path': {'files': {'name': 'data'}, 'dirs': {'name'}}}
        self.current_dir = "/"
        self.root_name = os.path.basename(os.path.abspath(root_dir_path)) or "VFS"
        self._load_from_disk(root_dir_path)

    def _load_from_disk(self, root_path):
        """Сканирует реальную директорию в память."""
        if not os.path.exists(root_path) or not os.path.isdir(root_path):
            self.fs["/"] = {"files": {}, "dirs": set()}
            return
        root_path = os.path.abspath(root_path)
        for root, dirs, files in os.walk(root_path):
            rel = os.path.relpath(root, root_path)
            v_path = "/" if rel == "." else "/" + rel.replace(os.sep, "/")
            if v_path not in self.fs:
                self.fs[v_path] = {"files": {}, "dirs": set()}
            for d in dirs:
                self.fs[v_path]["dirs"].add(d)
            for f in files:
                self._read_file_to_vfs(v_path, os.path.join(root, f), f)

    def _read_file_to_vfs(self, v_path, real_path, filename):
        """Вспомогательный метод безопасного чтения файла."""
        try:
            with open(real_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.fs[v_path]["files"][filename] = f.read()
        except Exception:
            self.fs[v_path]["files"][filename] = ""

    def _resolve_path(self, path):
        """Преобразует путь в канонический виртуальный абсолютный путь."""
        if path.startswith("/"):
            tokens = path.split("/")
        else:
            tokens = self.current_dir.split("/") + path.split("/")
        resolved = []
        for token in tokens:
            if token == "" or token == ".":
                continue
            if token == "..":
                if resolved:
                    resolved.pop()
            else:
                resolved.append(token)
        return "/" + "/".join(resolved)


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

    def _cmd_pwd(self, args):
        """Команда pwd (Этап 4)."""
        self.text_area.insert(tk.END, f"{self.vfs.current_dir}\n")
        return False

    def _cmd_ls(self, args):
        """Команда ls (Этап 4)."""
        t = self.vfs.current_dir if not args else self.vfs._resolve_path(args[0])
        if t in self.vfs.fs:
            d = sorted(list(self.vfs.fs[t]["dirs"]))
            f = sorted(list(self.vfs.fs[t]["files"].keys()))
            out = "  ".join(d + f)
            if out:
                self.text_area.insert(tk.END, f"{out}\n")
            return False
        self.text_area.insert(tk.END, f"ls: {args[0]}: No such directory\n")
        return "error"

    def _cmd_cd(self, args):
        """Команда cd (Этап 4)."""
        t = "/" if not args else self.vfs._resolve_path(args[0])
        if t in self.vfs.fs:
            self.vfs.current_dir = t
            return False
        self.text_area.insert(tk.END, f"cd: {args[0]}: No such directory\n")
        return "error"

    def _parse_tail_args(self, args):
        """Парсинг аргументов tail."""
        lines, file_idx = 10, 0
        if args[0] == "-n" and len(args) > 1:
            try:
                lines = int(args[1])
                file_idx = 2
            except ValueError:
                return None, None
        if file_idx >= len(args):
            return None, None
        return lines, args[file_idx]

    def _cmd_tail(self, args):
        """Команда tail (Этап 4)."""
        if not args:
            self.text_area.insert(tk.END, "tail: missing file operand\n")
            return "error"
        lines, filename = self._parse_tail_args(args)
        if lines is None:
            self.text_area.insert(tk.END, "tail: invalid arguments\n")
            return "error"
        path = self.vfs._resolve_path(filename)
        p_dir, f_name = "/".join(path.split("/")[:-1]) or "/", path.split("/")[-1]
        if p_dir in self.vfs.fs and f_name in self.vfs.fs[p_dir]["files"]:
            content = self.vfs.fs[p_dir]["files"][f_name].splitlines()
            res = content[-lines:]
            self.text_area.insert(tk.END, "\n".join(res) + ("\n" if res else ""))
            return False
        self.text_area.insert(tk.END, f"tail: {filename}: No such file\n")
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