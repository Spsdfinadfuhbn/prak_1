import unittest
import os
from prak_1 import VirtualFileSystem, ShellEmulatorGUI


class DummyTextArea:
    """Заглушка текстового поля Tkinter для перехвата вывода эмулятора."""

    def __init__(self):
        self.output = []

    def insert(self, index, text):
        self.output.append(text)

    def see(self, index):
        pass

    def mark_set(self, name, index):
        pass


class DummyRoot:
    """Заглушка главного окна Tkinter."""

    def destroy(self):
        pass


class TestShellEmulator(unittest.TestCase):

    def setUp(self):
        # Настройка виртуальной структуры файловой системы в памяти
        self.vfs = VirtualFileSystem("/invalid_path_to_trigger_empty_root")
        # Вручную наполняем vfs для изоляции тестов от диска (Этап 3)
        self.vfs.fs = {
            "/": {"files": {}, "dirs": {"dir1", "dir2"}},
            "/dir1": {"files": {"file1.txt": "line1\nline2\nline3\n"}, "dirs": {"subdir"}},
            "/dir1/subdir": {"files": {}, "dirs": set()},
            "/dir2": {"files": {"sample.txt": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n"}, "dirs": set()}
        }
        self.vfs.root_name = "TestVFS"

        # Создаем экземпляр GUI с заглушками вместо Tkinter
        self.gui = ShellEmulatorGUI.__new__(ShellEmulatorGUI)
        self.gui.vfs = self.vfs
        self.gui.text_area = DummyTextArea()
        self.gui.root = DummyRoot()

    # === ЭТАП 2: ТЕСТЫ КОНФИГУРАЦИИ И ПАРСИНГА ===
    def test_stage2_env_parsing(self):
        """Проверка раскрытия переменных окружения real-OS (Этап 1 & 2)."""
        os.environ["TEST_ENV_VAR"] = "dir1"
        parts, args = self.gui.parse_arguments("cd $TEST_ENV_VAR")
        self.assertEqual(parts, ["cd", "dir1"])
        self.assertEqual(args, ["dir1"])

    def test_stage2_unknown_command(self):
        """Проверка реакции на неизвестную команду."""
        res = self.gui.execute_command("invalidcommand arg1")
        self.assertEqual(res, "error")
        self.assertIn("invalidcommand: command not found\n", self.gui.text_area.output)

    # === ЭТАП 3: ТЕСТЫ СТРУКТУРЫ VFS ===
    def test_stage3_path_resolution(self):
        """Проверка канонизации путей (вложенность, точки) (Этап 3)."""
        self.vfs.current_dir = "/dir1"
        # Переход на уровень выше
        self.assertEqual(self.vfs._resolve_path(".."), "/")
        # Относительный путь вглубь
        self.assertEqual(self.vfs._resolve_path("subdir"), "/dir1/subdir")
        # Путь с текущей точкой и абсолютный
        self.assertEqual(self.vfs._resolve_path("/dir1/./subdir/../"), "/dir1")

    # === ЭТАП 4: ТЕСТЫ ОСНОВНЫХ КОМАНД (pwd, ls, cd, tail) ===
    def test_stage4_pwd(self):
        """Проверка команды pwd."""
        self.vfs.current_dir = "/dir1/subdir"
        self.gui.execute_command("pwd")
        self.assertIn("/dir1/subdir\n", self.gui.text_area.output)

    def test_stage4_cd_success_and_fail(self):
        """Проверка успешного перехода и обработки ошибки cd."""
        # Успех
        self.gui.execute_command("cd dir1")
        self.assertEqual(self.vfs.current_dir, "/dir1")
        # Ошибка
        res = self.gui.execute_command("cd nonexistent")
        self.assertEqual(res, "error")
        self.assertIn("cd: nonexistent: No such directory\n", self.gui.text_area.output)

    def test_stage4_ls(self):
        """Проверка вывода команды ls."""
        self.vfs.current_dir = "/dir1"
        self.gui.execute_command("ls")
        # Должен вывести и папку, и файл
        output_str = "".join(self.text_area_output())
        self.assertIn("subdir", output_str)
        self.assertIn("file1.txt", output_str)

    def test_stage4_tail_default(self):
        """Проверка команды tail без флага (вывод последних строк)."""
        self.vfs.current_dir = "/dir2"
        self.gui.execute_command("tail sample.txt")
        output = "".join(self.text_area_output())
        # Должен вывести строки от 2 до 11 (10 строк)
        self.assertTrue(output.startswith("2\n"))
        self.assertTrue(output.endswith("11\n"))

    def test_stage4_tail_with_flag(self):
        """Проверка tail с флагом -n (вывод заданного количества строк)."""
        self.vfs.current_dir = "/dir1"
        self.gui.execute_command("tail -n 2 file1.txt")
        output = "".join(self.text_area_output())
        self.assertEqual(output, "line2\nline3\n")

    # === ЭТАП 5: ТЕСТЫ ДОПОЛНИТЕЛЬНЫХ КОМАНД (rmdir, mv) ===
    def test_stage5_rmdir_success(self):
        """Успешное удаление пустой директории rmdir."""
        self.vfs.current_dir = "/dir1"
        self.gui.execute_command("rmdir subdir")
        self.assertNotIn("subdir", self.vfs.fs["/dir1"]["dirs"])
        self.assertNotIn("/dir1/subdir", self.vfs.fs)

    def test_stage5_rmdir_not_empty_error(self):
        """Ошибка при попытке удалить непустую директорию."""
        self.vfs.current_dir = "/"
        res = self.gui.execute_command("rmdir dir1")
        self.assertEqual(res, "error")
        self.assertIn("rmdir: dir1: Not empty\n", self.gui.text_area.output)

    def test_stage5_mv_file(self):
        """Перемещение и переименование файла с помощью mv."""
        self.vfs.current_dir = "/dir1"
        # Переименуем file1.txt в renamed.txt внутри /dir1
        self.gui.execute_command("mv file1.txt renamed.txt")
        self.assertNotIn("file1.txt", self.vfs.fs["/dir1"]["files"])
        self.assertIn("renamed.txt", self.vfs.fs["/dir1"]["files"])
        self.assertEqual(self.vfs.fs["/dir1"]["files"]["renamed.txt"], "line1\nline2\nline3\n")

    def test_stage5_mv_dir_subtree(self):
        """Перемещение папки со всей её структурой поддерева."""
        # Переместим /dir1/subdir внутрь /dir2
        self.gui.execute_command("mv /dir1/subdir /dir2")
        self.assertNotIn("subdir", self.vfs.fs["/dir1"]["dirs"])
        self.assertIn("subdir", self.vfs.fs["/dir2"]["dirs"])
        self.assertIn("/dir2/subdir", self.vfs.fs)

    def text_area_output(self):
        return self.gui.text_area.output


if __name__ == "__main__":
    unittest.main()
