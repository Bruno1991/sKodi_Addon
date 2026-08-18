# Empacotamento Kodi

Kodi não fornece AES-GCM seguro na biblioteca padrão do Python. O build gera um ZIP por plataforma e inclui um wheel binário de `cryptography`; não há fallback criptográfico artesanal. Execute `build_addon.py` para cada plataforma suportada e teste dentro da versão mínima do Kodi. A chave deve vir de integração segura do dispositivo; variável de ambiente serve apenas a instalações corporativas controladas.
