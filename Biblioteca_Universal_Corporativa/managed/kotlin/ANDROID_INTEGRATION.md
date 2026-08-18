# Integração Android

O código usa `javax.crypto`, `SecureRandom` e Base64 Java, disponíveis no Android moderno. Não use variável de ambiente no app: injete um `KeyProvider` backed por Android Keystore e mantenha a chave não exportável. AES-GCM no Keystore pode produzir a operação diretamente; nesse caso implemente um adapter que preserve o envelope v1. Autorização permanece no servidor e nenhuma chave compartilhada de backend deve ser embarcada no APK.
