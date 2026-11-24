# Auditoria inicial — 24/11/2026

- Windows 11 Pro, i5-10400F, RX 6600, aproximadamente 15,9 GiB de RAM visível; memória livre no instante da coleta aproximadamente 6,3 GiB.
- Python padrão 3.14.3; Python 3.12.15 isolado disponível via uv. OpenJarvis declara Python >=3.11 e <3.14.
- Node 24.16.0, Git, GitHub CLI, Codex autenticado via ChatGPT, FFmpeg, Graphify, Docker CLI e WSL presentes. Ollama, Obsidian, Blender e OpenSCAD não encontrados no PATH; isso não prova que não estejam instalados.
- OpenJarvis: projeto público Apache-2.0, ativo, com instruções Windows; não instalado nem homologado. https://github.com/open-jarvis/OpenJarvis
- Habblaud: projeto público MIT e ativo; documentação apresenta suporte Codex, mas requisitos citam macOS/Linux e há ressalva para hooks com Node 23–24.19. Windows deve ser testado isoladamente. https://github.com/marmottajr/habblaud
- GPU e aceleração de inferência não testadas. Não se deve inferir compatibilidade pela presença da GPU.
- GitHub: conta autorizada para este projeto: igorcastro1010. Não registre tokens.
