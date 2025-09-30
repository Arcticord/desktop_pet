import json
import os
from PIL import Image
import io
import pygame
from pygame.transform import flip
import base64
import uuid

class SimplePetCompiler:
    def __init__(self):
        self.metadata = {
            "format_version": "1.0",
            "created": "",
            "description": ""
        }
        self.animations = {}
    
    def set_metadata(self, description=""):
        """Установка метаданных"""
        from datetime import datetime
        self.metadata.update({
            "id": uuid.uuid4(),
            "created": datetime.now().isoformat(),
            "description": description
        })
    
    def add_animation(self, name, image_path, frame_width, frame_height, scale=1):
        """Добавление анимации из спрайтшита"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл {image_path} не найден")
        
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Вычисляем количество кадров
            cols = width // frame_width
            rows = height // frame_height
            frame_count = cols * rows
            
            # Конвертируем в PNG bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            image_data = img_bytes.getvalue()
            
            # Кодируем в base64
            image_data_b64 = base64.b64encode(image_data).decode('ascii')
            
            self.animations[name] = {
                "frame_width": frame_width,
                "frame_height": frame_height,
                "frame_count": frame_count,
                "scale": scale,
                "image_data": image_data_b64,
                "original_size": [width, height],
                "frames_layout": [cols, rows]
            }
    
    def compile(self, output_path):
        """Компиляция в .pet файл"""
        if not self.animations:
            raise ValueError("Нет анимаций для компиляции")
        
        # Подготавливаем структуру данных
        data_structure = {
            "metadata": self.metadata,
            "animations": self.animations
        }
        
        # Сериализуем JSON
        json_data = json.dumps(data_structure, ensure_ascii=False, indent=2)
        
        # Записываем в файл
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_data)
        
        print(f"Файл скомпилирован: {output_path}")
        return True

class SimplePetLoader:
    def __init__(self):
        self.animations = {}
    
    def load_pet_file(self, file_path):
        """Загрузка .pet файла"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        data = json.loads(content)
        return data

    def load_spritesheet(self, frame_width, frame_height, file_path=None, scale=1, image_data_b64=None):

        if image_data_b64 is not None:
            # Декодируем из base64
            image_data = base64.b64decode(image_data_b64)
            img_stream = io.BytesIO(image_data)
            sheet = pygame.image.load(img_stream).convert_alpha()
        elif file_path is not None:
            sheet = pygame.image.load(file_path).convert_alpha()
        frames = []
        for y in range(0, sheet.get_height(), frame_height):
            for x in range(0, sheet.get_width(), frame_width):
                frame = sheet.subsurface(pygame.Rect(x, y, frame_width, frame_height))
                if scale != 1:
                    new_size = (int(frame_width * scale), int(frame_height * scale))
                    frame = pygame.transform.scale(frame, new_size)
                frames.append(frame)
        return frames

    def load_all_animations(self, file_path):
        data = self.load_pet_file(file_path)
        
        animations_right = {}
        animations_left = {}
        
        for name, anim_data in data["animations"].items():
            # Загружаем оригинальные кадры (вправо)
            frames_right = self.load_spritesheet(
                image_data_b64=anim_data["image_data"],
                frame_width=anim_data["frame_width"], 
                frame_height=anim_data["frame_height"],
                scale=anim_data.get("scale", 1)
            )
            
            # Сохраняем в right
            animations_right[name] = frames_right
            
            # Создаем отраженные кадры (влево)
            frames_left = [pygame.transform.flip(frame, True, False) for frame in frames_right]
            animations_left[name] = frames_left
        
        return animations_right, animations_left
    
    def get_pet_info(self, file_path):
        """Получение информации об анимациях в файле"""
        data = self.load_pet_file(file_path)
        
        """
        print("=== Метаданные ===")
        for key, value in data["metadata"].items():
            print(f"{key}: {value}")
        
        print("\n=== Анимации ===")
        for name, anim in data["animations"].items():
            print(f"{name}:")
            print(f"  - Размер кадра: {anim['frame_width']}x{anim['frame_height']}")
            print(f"  - Количество кадров: {anim['frame_count']}")
            print(f"  - Масштаб: {anim.get('scale', 1)}")
            print(f"  - Расположение: {anim['frames_layout'][0]}x{anim['frames_layout'][1]}")
            print(f"  - Размер данных: {len(anim['image_data'])} символов base64")
        """
        return data

# Тестирование
"""if __name__ == "__main__":
     # Компиляция
    compiler = SimplePetCompiler()
    compiler.set_metadata("Анимации моего питомца")
    
    compiler.add_animation("Анимация1", "Спрайтшит1.png", 32, 32, 2)
    compiler.add_animation("Анимация2", "Спрайтшит2.png", 32, 32, 2)
    compiler.add_animation("Анимация3", "Спрайтшит3.png", 32, 32, 2)
    
    compiler.compile("pet.pet")
"""