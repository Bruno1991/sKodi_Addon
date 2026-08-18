using System.Security.Cryptography;

namespace Corporate.Security;

public sealed class EnvironmentKeyProvider : IKeyProvider, IDisposable
{
    public const string VariableName = "MBUC_AES_KEY_BASE64";
    private readonly byte[] _key;
    private bool _disposed;

    public EnvironmentKeyProvider()
    {
        var encoded = Environment.GetEnvironmentVariable(VariableName);
        if (string.IsNullOrWhiteSpace(encoded))
        {
            throw new CryptoContractException("missing_key", $"Environment variable {VariableName} is required.");
        }

        try
        {
            _key = Convert.FromBase64String(encoded);
        }
        catch (FormatException exception)
        {
            throw new CryptoContractException("invalid_key", $"Environment variable {VariableName} is not valid Base64.", exception);
        }

        if (_key.Length != 32)
        {
            CryptographicOperations.ZeroMemory(_key);
            throw new CryptoContractException("invalid_key", "AES-256-GCM requires exactly 32 key bytes.");
        }
    }

    public ReadOnlyMemory<byte> GetKey()
    {
        ObjectDisposedException.ThrowIf(_disposed, this);
        return _key;
    }

    public void Dispose()
    {
        if (_disposed) return;
        CryptographicOperations.ZeroMemory(_key);
        _disposed = true;
    }
}
