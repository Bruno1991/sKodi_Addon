# Segurança Arduino/ESP32

`WiFiClientSecure` exige um trust anchor configurado pelo integrador com `setCACert` ou mecanismo equivalente. O exemplo não chama `setInsecure`; sem CA válida, a conexão deve falhar. Credenciais Wi-Fi e chave AES não pertencem ao firmware ou repositório: provisionar por canal seguro, NVS criptografado/secure element e política de rotação. Testar perda de sinal, relógio inválido, certificado expirado, watchdog e limite de payload em hardware real.
