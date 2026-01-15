"""Script para converter icon.png para icon.ico"""
from PIL import Image
import os

# Encontrar o diretório do script
script_dir = os.path.dirname(os.path.abspath(__file__))
assets_dir = os.path.join(script_dir, 'assets')

# Caminhos
png_path = os.path.join(assets_dir, 'icon.png')
ico_path = os.path.join(assets_dir, 'icon.ico')

# Converter
img = Image.open(png_path)
img.save(ico_path, format='ICO', sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
print(f'Icon converted: {ico_path}')
