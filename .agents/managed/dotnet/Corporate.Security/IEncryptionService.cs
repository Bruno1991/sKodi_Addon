namespace Corporate.Security;

public interface IEncryptionService
{
    string Encrypt(ReadOnlySpan<byte> plaintext, ReadOnlySpan<byte> associatedData);
    byte[] Decrypt(string envelope, ReadOnlySpan<byte> associatedData);
}
