using System.Security.Cryptography;
using Microsoft.Extensions.Logging;

namespace Corporate.Security;

public sealed class AesGcmEncryptionService(IKeyProvider keyProvider, ILogger<AesGcmEncryptionService> logger) : IEncryptionService
{
    private const string Prefix = "v1.";
    private const int NonceSize = 12;
    private const int TagSize = 16;

    public string Encrypt(ReadOnlySpan<byte> plaintext, ReadOnlySpan<byte> associatedData)
    {
        ValidateAssociatedData(associatedData);
        var key = keyProvider.GetKey();
        ValidateKey(key.Span);

        Span<byte> nonce = stackalloc byte[NonceSize];
        RandomNumberGenerator.Fill(nonce);
        var ciphertext = new byte[plaintext.Length];
        Span<byte> tag = stackalloc byte[TagSize];

        try
        {
            using var aes = new AesGcm(key.Span, TagSize);
            aes.Encrypt(nonce, plaintext, ciphertext, tag, associatedData);

            var payload = new byte[NonceSize + TagSize + ciphertext.Length];
            nonce.CopyTo(payload);
            tag.CopyTo(payload.AsSpan(NonceSize));
            ciphertext.CopyTo(payload.AsSpan(NonceSize + TagSize));
            logger.LogInformation("AES-GCM encryption completed. PlaintextLength={PlaintextLength} Outcome={Outcome}", plaintext.Length, "success");
            return Prefix + Base64UrlEncode(payload);
        }
        catch (CryptographicException exception)
        {
            logger.LogError(exception, "AES-GCM encryption failed. Outcome={Outcome} ErrorCode={ErrorCode}", "failure", "encryption_failed");
            throw new CryptoContractException("encryption_failed", "Encryption failed.", exception);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(ciphertext);
        }
    }

    public byte[] Decrypt(string envelope, ReadOnlySpan<byte> associatedData)
    {
        ArgumentNullException.ThrowIfNull(envelope);
        ValidateAssociatedData(associatedData);
        if (!envelope.StartsWith(Prefix, StringComparison.Ordinal))
        {
            throw new CryptoContractException("invalid_envelope", "Unsupported crypto envelope version.");
        }

        byte[] payload;
        try
        {
            payload = Base64UrlDecode(envelope[Prefix.Length..]);
        }
        catch (FormatException exception)
        {
            throw new CryptoContractException("invalid_envelope", "Envelope payload is not valid Base64URL.", exception);
        }

        if (payload.Length < NonceSize + TagSize)
        {
            throw new CryptoContractException("invalid_envelope", "Envelope payload is truncated.");
        }

        var key = keyProvider.GetKey();
        ValidateKey(key.Span);
        var nonce = payload.AsSpan(0, NonceSize);
        var tag = payload.AsSpan(NonceSize, TagSize);
        var ciphertext = payload.AsSpan(NonceSize + TagSize);
        var plaintext = new byte[ciphertext.Length];

        try
        {
            using var aes = new AesGcm(key.Span, TagSize);
            aes.Decrypt(nonce, ciphertext, tag, plaintext, associatedData);
            logger.LogInformation("AES-GCM decryption completed. PlaintextLength={PlaintextLength} Outcome={Outcome}", plaintext.Length, "success");
            return plaintext;
        }
        catch (CryptographicException exception)
        {
            CryptographicOperations.ZeroMemory(plaintext);
            logger.LogWarning("AES-GCM authentication failed. Outcome={Outcome} ErrorCode={ErrorCode}", "failure", "authentication_failed");
            throw new CryptoContractException("authentication_failed", "Envelope authentication failed.", exception);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(payload);
        }
    }

    private static void ValidateKey(ReadOnlySpan<byte> key)
    {
        if (key.Length != 32) throw new CryptoContractException("invalid_key", "AES-256-GCM requires exactly 32 key bytes.");
    }

    private static void ValidateAssociatedData(ReadOnlySpan<byte> associatedData)
    {
        if (associatedData.IsEmpty) throw new CryptoContractException("invalid_aad", "Associated data is required.");
    }

    private static string Base64UrlEncode(ReadOnlySpan<byte> value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static byte[] Base64UrlDecode(string value)
    {
        var normalized = value.Replace('-', '+').Replace('_', '/');
        normalized += normalized.Length % 4 switch { 0 => string.Empty, 2 => "==", 3 => "=", _ => throw new FormatException("Invalid Base64URL length.") };
        return Convert.FromBase64String(normalized);
    }
}
