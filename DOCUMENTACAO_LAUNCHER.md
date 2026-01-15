# 📚 Documentação do Baiak-Zika Launcher

## 🔗 Links Importantes

| Recurso | URL |
|---------|-----|
| **GitHub Repo** | https://github.com/pauloandre45/baiak-zika-launcher |
| **Releases** | https://github.com/pauloandre45/baiak-zika-launcher/releases |
| **Gist Config** | https://gist.github.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad |
| **Versão Atual** | v1.0.11 |

---

## 📦 Estrutura do Projeto

```
/home/launcher_baiak_zika/
├── launcher.py          # Código principal do launcher
├── icon.ico             # Ícone do Tibia (personagem)
├── assets/              # Imagens do launcher (background, logo, etc)
├── installer/
│   └── setup.iss        # Script do Inno Setup (instalador)
├── .github/workflows/
│   ├── build.yml        # Build do launcher EXE
│   └── build-installer.yml  # Build do instalador
└── local_config.json    # Versões locais (cliente usa isso)
```

---

## 🔄 Como Atualizar os Assets do Cliente

### Passo a Passo:

1. **Coloque os novos assets** na pasta `/home/atualizaçoes/`

2. **Compacte em ZIP:**
```bash
cd /home/atualizaçoes
zip -r assets_v1.X.zip assets/
```

3. **Upload no GitHub Release v1.0.0:**
```bash
cd /home/launcher_baiak_zika
gh release upload v1.0.0 /home/atualizaçoes/assets_v1.X.zip --clobber
```

4. **Atualize o Gist** (https://gist.github.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad):
```json
{
  "clientVersion": "1.0.11",
  "assetsVersion": "1.0.X",  // <-- Incrementar aqui
  "downloadUrl": "https://github.com/pauloandre45/baiak-zika-launcher/releases/download/v1.0.11/Baiak-Zika-Setup.exe",
  "assetsDownloadUrl": "https://github.com/pauloandre45/baiak-zika-launcher/releases/download/v1.0.0/assets_v1.X.zip"
}
```

5. **Pronto!** Os clientes vão ver "ATUALIZAR ASSETS" automaticamente.

---

## 🛠️ Como Atualizar o Launcher (EXE)

1. Faça as alterações no `launcher.py`

2. Commit e push:
```bash
cd /home/launcher_baiak_zika
git add -A
git commit -m "Descrição da mudança"
git push
```

3. O GitHub Actions vai compilar automaticamente

4. Baixe o instalador:
```bash
gh run list --limit 1
gh run download <ID_DO_RUN>
```

5. Crie nova release:
```bash
gh release create v1.0.XX --title "Título" --notes "Descrição" ./Baiak-Zika-Installer/Baiak-Zika-Setup.exe
```

6. Atualize o `clientVersion` no Gist

---

## ⚙️ Configuração do Gist (Servidor)

O launcher busca configurações deste Gist:
- **ID:** `e59926d5c0c8cbc9d225e06db7e446ad`
- **URL Raw:** `https://gist.githubusercontent.com/pauloandre45/e59926d5c0c8cbc9d225e06db7e446ad/raw/launcher_config.json`

### Estrutura:
```json
{
  "clientVersion": "1.0.11",      // Versão do launcher EXE
  "assetsVersion": "1.0.1",       // Versão dos assets
  "downloadUrl": "URL do instalador",
  "assetsDownloadUrl": "URL do ZIP de assets"
}
```

---

## 🎮 Funcionalidades do Launcher

- ✅ Verificação automática de atualizações
- ✅ Download parcial (só assets modificados)
- ✅ Botão JOGAR oculto quando há atualização pendente
- ✅ Instalador profissional (AppData\Local)
- ✅ Atalho na área de trabalho com ícone do Tibia
- ✅ Desinstalador no Painel de Controle

---

## 📝 Comandos Úteis

```bash
# Ver releases
gh release list

# Ver workflows rodando
gh run list

# Acompanhar um workflow
gh run watch <ID>

# Baixar artefatos de um workflow
gh run download <ID>

# Criar release
gh release create vX.X.X --title "Título" arquivo.exe

# Editar Gist
gh gist edit e59926d5c0c8cbc9d225e06db7e446ad
```

---

## 📅 Histórico de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| v1.0.11 | 15/01/2026 | Versão final com ícone correto no EXE |
| v1.0.10 | 15/01/2026 | Novo ícone do Tibia |
| v1.0.9 | 15/01/2026 | Instalador profissional |
| v1.0.8 | 15/01/2026 | Botão JOGAR oculto quando há update |

---

*Documentação criada em 15/01/2026*
