# 🎮 Assets do Launcher Baiak-Zika

## Imagens necessárias

Coloque as seguintes imagens nesta pasta:

### 1. `background.png`
- **Tamanho recomendado:** 700x450 pixels ou maior
- **Descrição:** Imagem de fundo do launcher (a cena épica com castelos e lava)
- Use a imagem de fundo com o cenário roxo/vermelho

### 2. `logo.png`
- **Tamanho recomendado:** 350-400 pixels de largura
- **Descrição:** Logo "Baiak-Zika" com efeito dourado/vermelho
- Deve ter fundo transparente (PNG com alpha)

### 3. `icon.ico` (na pasta principal do launcher)
- **Tamanho:** 256x256 pixels
- **Descrição:** Ícone do aplicativo (o "BZ" ou a caveira)
- Formato ICO para Windows

---

## Como recortar as imagens

### No Photoshop/GIMP:
1. Abra a imagem completa
2. Use a ferramenta de seleção para recortar cada elemento
3. Exporte como PNG com transparência

### Online (gratuito):
- https://www.remove.bg - Remove fundo automaticamente
- https://www.photopea.com - Editor online tipo Photoshop

---

## Estrutura final:
```
launcher_baiak_zika/
├── launcher.py
├── icon.ico          ← Ícone do BZ ou caveira
├── local_config.json
└── assets/
    ├── background.png  ← Cenário épico
    └── logo.png        ← Logo Baiak-Zika
```
