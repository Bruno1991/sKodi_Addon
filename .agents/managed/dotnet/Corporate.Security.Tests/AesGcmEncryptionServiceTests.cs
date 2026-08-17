using System.Text;
using Microsoft.Extensions.Logging.Abstractions;

namespace Corporate.Security.Tests;

public sealed class AesGcmEncryptionServiceTests
{
    private static readonly byte[] Key = Enumerable.Range(1, 32).Select(value => (byte)value).ToArray();
    private static readonly byte[] Aad = Encoding.UTF8.GetBytes("tenant:acme|purpose:profile");

    [Fact]
    public void EncryptThenDecryptReturnsOriginalPlaintext()
    {
        var service = CreateService();
        var plaintext = Encoding.UTF8.GetBytes("corporate secret");
        var envelope = service.Encrypt(plaintext, Aad);
        var decrypted = service.Decrypt(envelope, Aad);
        Assert.Equal(plaintext, decrypted);
        Assert.True(envelope.StartsWith("v1.", StringComparison.Ordinal));
    }

    [Fact]
    public void DecryptRejectsTamperedCiphertext()
    {
        var service = CreateService();
        var envelope = service.Encrypt(Encoding.UTF8.GetBytes("secret"), Aad);
        var replacement = envelope[^1] == 'A' ? 'B' : 'A';
        var tampered = envelope[..^1] + replacement;
        var exception = Assert.Throws<CryptoContractException>(() => service.Decrypt(tampered, Aad));
        Assert.Equal("authentication_failed", exception.Code);
    }

    [Fact]
    public void DecryptRejectsDifferentAssociatedData()
    {
        var service = CreateService();
        var envelope = service.Encrypt(Encoding.UTF8.GetBytes("secret"), Aad);
        var wrongAad = Encoding.UTF8.GetBytes("tenant:other|purpose:profile");
        var exception = Assert.Throws<CryptoContractException>(() => service.Decrypt(envelope, wrongAad));
        Assert.Equal("authentication_failed", exception.Code);
    }

    private static AesGcmEncryptionService CreateService() =>
        new(new StaticKeyProvider(Key), NullLogger<AesGcmEncryptionService>.Instance);

    private sealed class StaticKeyProvider(byte[] key) : IKeyProvider
    {
        public ReadOnlyMemory<byte> GetKey() => key;
    }
}
