namespace Corporate.Security;

public sealed class CryptoContractException : Exception
{
    public CryptoContractException(string code, string message) : base(message) => Code = code;
    public CryptoContractException(string code, string message, Exception innerException) : base(message, innerException) => Code = code;
    public string Code { get; }
}
