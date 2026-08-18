import { decrypt, encrypt, generateKey, utf8 } from "./aes-gcm.js";

const form = document.querySelector("#crypto-form");
const result = document.querySelector("#result");
if (!(form instanceof HTMLFormElement) || !(result instanceof HTMLOutputElement)) throw new Error("Required page elements are missing.");
const key = await generateKey();
form.addEventListener("submit", async event => {
  event.preventDefault();
  const plaintextElement = document.querySelector("#plaintext");
  const aadElement = document.querySelector("#aad");
  if (!(plaintextElement instanceof HTMLTextAreaElement) || !(aadElement instanceof HTMLInputElement)) return;
  try {
    const envelope = await encrypt(key, utf8(plaintextElement.value), utf8(aadElement.value));
    const recovered = new TextDecoder().decode(await decrypt(key, envelope, utf8(aadElement.value)));
    result.textContent = recovered === plaintextElement.value ? `Validação concluída. Envelope: ${envelope}` : "Falha de consistência.";
  } catch {
    result.textContent = "A operação criptográfica falhou.";
  }
});
