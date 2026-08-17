namespace Corporate.Security;

public interface IKeyProvider
{
    ReadOnlyMemory<byte> GetKey();
}
