import pygame
import ctypes
import shutil
import os
import threading
import tkinter as tk
from tkinter import filedialog
from PIL import Image
import pystray
import random
from pet_compile import SimplePetLoader

# Константы Windows API
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
GWL_EXSTYLE = -20
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
LWA_ALPHA = 0x00000002
LWA_COLORKEY = 0x00000001

class PetManager:
    def __init__(self):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.NOFRAME)
        
        self.hwnd = pygame.display.get_wm_info()['window']
        
        ex_style = ctypes.windll.user32.GetWindowLongA(self.hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongA(self.hwnd, GWL_EXSTYLE, 
                                          ex_style | WS_EX_LAYERED | WS_EX_TOOLWINDOW)
        
        ctypes.windll.user32.SetLayeredWindowAttributes(self.hwnd, 0x00FFFFFF, 255, LWA_COLORKEY)

        self.click_pos = None
        self.pets = []
        self.running = True
        self.show_debug = False
        self.menu_show = False
        self.menu_window = None  # Ссылка на tkinter окно (self.root)
        self.setup_tray()  

    def add_pet(self, pet):
        self.pets.append(pet)
        
    def setup_tray(self):

        def exit_action(icon, item):
            for pet in self.pets:
                pet.running = False
            self.running = False

            try:
                if self.menu_window:
                    self.menu_window.destroy()
                if hasattr(self, 'menu_window') and self.menu_window:
                    try:
                        self.menu_window.after(0, self.menu_window.quit)
                        self.menu_window.after(0, self.menu_window.destroy)
                    except:
                        pass
            except:
                pass  # Игнорируем ошибки если окно уже уничтожено
            icon.stop()
            
        def debug_action(icon, item):
            self.show_debug = not self.show_debug

        def menu_action(icon, item):
            self.show_menu()

        image = Image.new('RGB', (64, 64), 'red')
        menu = pystray.Menu(
            pystray.MenuItem('Меню', menu_action),
            pystray.MenuItem('Debug', debug_action),
            pystray.MenuItem('Выход', exit_action)
        )
        self.icon = pystray.Icon('pet', image, menu=menu)
        self.tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        self.tray_thread.start()

    def show_menu(self):
        """Показывает tkinter меню"""
        try:
            # Пробуем проверить существует ли окно
            if self.menu_window and self.menu_window.winfo_exists():
                self.menu_window.focus_force()
            else:
                # Создаем новое меню
                pet_menu = PetMenu(self)
                self.menu_window = pet_menu.root
        except:
            # Если произошла ошибка (окно уничтожено), создаем новое
            pet_menu = PetMenu(self)
            self.menu_window = pet_menu.root

    def handle_selection(self, mouse_pos):
        clicked_pet = None
        
        # Проверяем всех питомцев с конца (верхние слои)
        for pet in reversed(self.pets):
            if self.is_point_on_pet(mouse_pos, pet):
                clicked_pet = pet
                break
        
        # Обновляем состояние выделения
        for pet in self.pets:
            pet.is_selected = (pet == clicked_pet)
    
    def is_point_on_pet(self, point, pet):
        """Проверяет, находится ли клик на питомце"""
        if not hasattr(pet, 'animations_right') or pet.current_animation not in pet.animations_right:
            return False
            
        # Получаем текущий кадр питомца
        frames = pet.animations_right[pet.current_animation]
        if not frames or pet.current_frame >= len(frames):
            return False
            
        frame = frames[pet.current_frame]
        pet_rect = frame.get_rect(topleft=(pet.x_pos, pet.y_pos))
        
        return pet_rect.collidepoint(point)

    def run(self):
        clock = pygame.time.Clock()
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.click_pos = event.pos
                        self.handle_selection(event.pos)
                    
            if not self.running:
                break
                
            # Обновляем всех питомцев
            for pet in self.pets:
                pet.update()
            
            # Очищаем экран
            self.screen.fill((255, 255, 255))
            
            # Рисуем всех питомцев
            for pet in self.pets:
                pet.draw(self.screen)
            
            # Рисуем debug информацию
            self.draw_debug_info(screen=self.screen, click_pos=self.click_pos)
            
            # Обновляем дисплей
            pygame.display.flip()
            clock.tick(60)

    def draw_debug_info(self, screen, click_pos):
        if not self.show_debug:
            return 

        debug_width, debug_height = 280, 200
        debug_surface = pygame.Surface((debug_width, debug_height), pygame.SRCALPHA)
        debug_surface.fill((0, 0, 0, 200))
        
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click_pos = event.pos

        font = pygame.font.SysFont('Arial', 22)
        lines = [
            f"Is running: {self.running}",
            f"Pet count: {len(self.pets)}",
            f"Show debug: {self.show_debug}",
            f"Clicked: {click_pos}",
            f"Menu open: {self.menu_show}",
            f"Frame: {pygame.time.get_ticks()}",
            "=== Debug Mode ==="
        ]
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, False, (255, 255, 255))
            debug_surface.blit(text_surface, (10, 10 + i * 20))
        
        debug_x = self.screen_width - debug_width - 10
        debug_y = self.screen_height - debug_height - 10
        
        pygame.draw.rect(debug_surface, (255, 255, 255), 
                        debug_surface.get_rect(), 1)

        screen.blit(debug_surface, (debug_x, debug_y))

class DesktopPet:
    def __init__(self, asset_file):
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)            # Ширина экрана
        self.screen_height = user32.GetSystemMetrics(1)           # Высота экрана 
        self.running = True                                       # Отображение питомца
        self.facing_right = True                                  # Направление питомца вправо
        self.is_selected = False                                  # Статус выбора питомца
        self.current_frame = 0                                    # Текущий кадр
        self.last_update = pygame.time.get_ticks()                # 
        self.animation_speed = 0.4                                # Скорость анимации
        self.current_animation = 'idle'                           # Текущая анимация
        self.x_pos, self.y_pos = self.get_random_coordinates()    # Устанавливаем случайную стартовую позицию
        self.wander_target = None                                 # Целевая точка (x, y)
        self.prev_target = None                                   # Предыдущая цель блуждания
        self.wander_speed = 2                                     # Скорость движения
        self.last_wander_time = 0                                 # Время последнего блуждания
        self.ui = {}

        self.pet_loader = SimplePetLoader()
        try:
            self.animations_right, self.animations_left = self.pet_loader.load_all_animations(asset_file)
        except:
            self.animations_right, self.animations_left = self.pet_loader.load_all_animations("default.pet")
        self.load_ui()

    def get_random_coordinates(self):
        return (random.randint(0, self.screen_width - 100), random.randint(0, self.screen_height - 100))

    def load_ui(self):
        self.ui['selection'] = self.pet_loader.load_spritesheet(
            frame_height=10,
            frame_width=32,
            scale=2,
            file_path="Assets/UI/Selection_circle.png"
        )

    def set_wander_target(self, target_x, target_y):
        self.wander_target = (target_x, target_y)
        self.current_frame = 0
        self.current_animation = 'run'  # меняем анимацию на бег

    def update(self):
        """Обновляет состояние питомца (вызывается каждый кадр)"""
        current_time = pygame.time.get_ticks()

        # Логика перемещения
        if self.wander_target is not None:
            target_x, target_y = self.wander_target
            dx = target_x - self.x_pos
            dy = target_y - self.y_pos
            distance = (dx**2 + dy**2)**0.5
            
            if distance < self.wander_speed:
                self.x_pos = target_x
                self.y_pos = target_y
                self.wander_target = None
                self.current_animation = 'idle'
                self.current_frame = 0
            else:
                self.x_pos += (dx / distance) * self.wander_speed
                self.y_pos += (dy / distance) * self.wander_speed
                self.facing_right = dx > 0

        # Логика блуждания
        if current_time - self.last_wander_time >= 10000 and self.current_animation != 'run':
            self.last_wander_time = current_time
            if random.random() < 0.60:
                target_x, target_y = self.get_random_coordinates()
                self.set_wander_target(target_x, target_y)

        # Анимация
        if current_time - self.last_update > self.animation_speed * 1000:
            self.current_frame = (self.current_frame + 1) % len(self.animations_right[self.current_animation])
            self.last_update = current_time

    def draw(self, screen):
        """Отрисовывает питомца (вызывается каждый кадр)"""

        selection_y_offset = 26 * 2

        if self.facing_right:
            frames = self.animations_right[self.current_animation]
        else:
            frames = self.animations_left[self.current_animation]
        screen.blit(frames[self.current_frame], (self.x_pos, self.y_pos))
        if self.is_selected:
            screen.blit(self.ui['selection'][0], (self.x_pos, self.y_pos + selection_y_offset))

class PetMenu:
    def __init__(self, pet_manager):
        self.pet_manager = pet_manager
        self.pet_manager.menu_show = True

        self.mypets_dir = "MyPets"
        os.makedirs(self.mypets_dir, exist_ok=True)
        
        # Создаем главное окно
        self.root = tk.Tk()
        self.root.title("Pet Manager")
        self.root.geometry("300x400")
        self.root.resizable(False, False)
        self.root.configure(bg='#2b2b2b')
        
        # Делаем окно поверх остальных
        self.root.attributes('-topmost', True)
        
        # Центрируем окно
        self.center_window()
        
        # Создаем стиль
        self.setup_styles()
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.root.mainloop()
    
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_styles(self):
        """Настраивает стили для виджетов"""
        self.style = {
            'bg': '#2b2b2b',
            'fg': 'white',
            'button_bg': '#404040',
            'button_hover': '#505050',
            'button_active': '#606060',
            'accent_bg': '#4CAF50',
            'accent_hover': '#45a049',
            'warning_bg': '#f44336',
            'warning_hover': '#da190b'
        }
    
    def create_widgets(self):
        """Создает все элементы интерфейса"""
        # Заголовок
        title_label = tk.Label(
            self.root, 
            text="Menu", 
            font=('Arial', 16, 'bold'),
            bg=self.style['bg'],
            fg=self.style['fg']
        )
        title_label.pack(pady=20)
        
        # Информация о питомцах
        info_frame = tk.Frame(self.root, bg=self.style['bg'])
        info_frame.pack(pady=10)
        
        self.pet_count_label = tk.Label(
            info_frame,
            text=f"Активных питомцев: {len(self.pet_manager.pets)}",
            font=('Arial', 10),
            bg=self.style['bg'],
            fg=self.style['fg']
        )
        self.pet_count_label.pack()
        
        # Кнопки управления
        buttons_frame = tk.Frame(self.root, bg=self.style['bg'])
        buttons_frame.pack(pady=20)

        # Кнопка добавления из MyPets
        mypets_btn = tk.Button(
            buttons_frame,
            text="Добавить недавнего",
            font=('Arial', 10),
            bg=self.style['accent_bg'],
            fg='white',
            activebackground=self.style['accent_hover'],
            activeforeground='white',
            width=25,
            height=2,
            command=self.add_from_mypets,
            cursor='hand2'
        )
        mypets_btn.pack(pady=5)
        
        # Кнопка загрузки из файла (теперь с копированием в MyPets)
        load_file_btn = tk.Button(
            buttons_frame,
            text="Загрузить из файла",
            font=('Arial', 10),
            bg=self.style['button_bg'],
            fg='white',
            activebackground=self.style['button_hover'],
            activeforeground='white',
            width=25,
            height=2,
            command=self.load_from_file,
            cursor='hand2'
        )
        load_file_btn.pack(pady=5)
        
        # Кнопка удаления всех питомцев
        clear_btn = tk.Button(
            buttons_frame,
            text="Удалить всех питомцев",
            font=('Arial', 10),
            bg=self.style['warning_bg'],
            fg='white',
            activebackground=self.style['warning_hover'],
            activeforeground='white',
            width=25,
            height=2,
            command=self.clear_all_pets,
            cursor='hand2'
        )
        clear_btn.pack(pady=5)
        
        # Кнопка скрытия/показа debug
        debug_btn = tk.Button(
            buttons_frame,
            text="Debug",
            font=('Arial', 10),
            bg=self.style['button_bg'],
            fg='white',
            activebackground=self.style['button_hover'],
            activeforeground='white',
            width=25,
            height=2,
            command=self.toggle_debug,
            cursor='hand2'
        )
        debug_btn.pack(pady=5)
        
        # Список питомцев
        list_frame = tk.Frame(self.root, bg=self.style['bg'])
        list_frame.pack(pady=10, fill='both', expand=True)
        
        list_label = tk.Label(
            list_frame,
            text="Активные питомцы:",
            font=('Arial', 10, 'bold'),
            bg=self.style['bg'],
            fg=self.style['fg']
        )
        list_label.pack()
        
        # Прокручиваемый список питомцев
        self.pet_listbox = tk.Listbox(
            list_frame,
            bg='#404040',
            fg='white',
            selectbackground='#4CAF50',
            height=6
        )
        self.pet_listbox.pack(fill='both', expand=True, pady=5)
        
        # Кнопка удаления выбранного питомца
        remove_selected_btn = tk.Button(
            list_frame,
            text="Удалить выбранного",
            font=('Arial', 9),
            bg=self.style['warning_bg'],
            fg='white',
            activebackground=self.style['warning_hover'],
            command=self.remove_selected_pet,
            cursor='hand2'
        )
        remove_selected_btn.pack(pady=5)
        
        # Обновляем список питомцев
        self.update_pet_list()
    
    def load_from_file(self):
        """Загружает питомца из .pet файла через проводник и копирует в MyPets"""
        file_path = filedialog.askopenfilename(
            title="Выберите .pet файл",
            filetypes=[("Pet files", "*.pet"), ("All files", "*.*")],
            initialdir="."  # Текущая директория
        )
        
        if file_path:
            try:
                # Копируем файл в MyPets
                copied_path = self.copy_to_mypets(file_path)
                if copied_path:
                    # Загружаем из скопированного файла
                    new_pet = DesktopPet(asset_file=copied_path)
                    self.pet_manager.add_pet(new_pet)
                    self.update_pet_list()
                    print(f"Успешно загружен питомец из: {file_path} (скопирован в MyPets)")
                else:
                    tk.messagebox.showerror("Ошибка", "Не удалось скопировать файл в MyPets")
                    
            except Exception as e:
                print(f"Ошибка загрузки файла {file_path}: {e}")
                tk.messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")
    
    def get_available_pets(self):
        """Возвращает список доступных .pet файлов в папке MyPets"""
        pet_files = []
        try:
            for file in os.listdir(self.mypets_dir):
                if file.lower().endswith('.pet'):
                    full_path = os.path.join(self.mypets_dir, file)
                    pet_files.append((file, full_path))
        except Exception as e:
            print(f"Ошибка чтения папки MyPets: {e}")
        
        return pet_files

    def clear_all_pets(self):
        """Удаляет всех питомцев"""
        self.pet_manager.pets.clear()
        self.update_pet_list()

    def copy_to_mypets(self, source_path):
        """Копирует .pet файл в папку MyPets"""
        try:
            filename = os.path.basename(source_path)
            destination = os.path.join(self.mypets_dir, filename)
            
            # Если файл уже существует, добавляем номер
            counter = 1
            base_name = filename[:-4]  # убираем .pet
            while os.path.exists(destination):
                new_filename = f"{base_name}_{counter}.pet"
                destination = os.path.join(self.mypets_dir, new_filename)
                counter += 1
            
            shutil.copy2(source_path, destination)
            return destination
        except Exception as e:
            print(f"Ошибка копирования файла: {e}")
            return None
    
    def toggle_debug(self):
        """Переключает режим debug"""
        self.pet_manager.show_debug = not self.pet_manager.show_debug
    
    def remove_selected_pet(self):
        """Удаляет выбранного питомца из списка"""
        selection = self.pet_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.pet_manager.pets):
                del self.pet_manager.pets[index]
                self.update_pet_list()
    
    def update_pet_list(self):
        """Обновляет список питомцев и счетчик"""
        self.pet_listbox.delete(0, tk.END)
        
        for i, pet in enumerate(self.pet_manager.pets):
            pet_type = os.path.basename(pet.pet_loader.current_file) if hasattr(pet.pet_loader, 'current_file') else "Unknown"
            self.pet_listbox.insert(tk.END, f"{i+1}. {pet_type} - ({int(pet.x_pos)},{int(pet.y_pos)})")
        
        self.pet_count_label.config(text=f"Активных питомцев: {len(self.pet_manager.pets)}")
    
    def add_from_mypets(self):
        """Добавляет питомца из папки MyPets"""
        available_pets = self.get_available_pets()
        
        if not available_pets:
            tk.messagebox.showinfo("Информация", "В папке MyPets нет .pet файлов")
            return
        
        # Создаем меню выбора
        mypets_menu = tk.Menu(self.root, tearoff=0, bg='#404040', fg='white')
        
        for filename, full_path in available_pets:
            display_name = filename[:-4]  # убираем .pet для красоты
            mypets_menu.add_command(
                label=display_name,
                command=lambda fp=full_path: self.load_mypets_pet(fp),
                background='#404040',
                foreground='white',
                activebackground='#4CAF50',
                activeforeground='white'
            )
        
        # Показываем меню рядом с кнопкой
        mypets_menu.post(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def load_mypets_pet(self, file_path):
        """Загружает питомца из папки MyPets"""
        try:
            new_pet = DesktopPet(asset_file=file_path)
            self.pet_manager.add_pet(new_pet)
            self.update_pet_list()
            print(f"Успешно загружен питомец из MyPets: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Ошибка загрузки файла {file_path}: {e}")
            tk.messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def on_close(self):
        """Обрабатывает закрытие окна"""
        self.pet_manager.menu_show = False
        self.root.destroy()
    
if __name__ == "__main__":
    game = PetManager()
    game.run()