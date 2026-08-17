using Microsoft.Extensions.DependencyInjection;

namespace Corporate.Security;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddCorporateEncryption(this IServiceCollection services)
    {
        ArgumentNullException.ThrowIfNull(services);
        services.AddSingleton<IKeyProvider, EnvironmentKeyProvider>();
        services.AddSingleton<IEncryptionService, AesGcmEncryptionService>();
        return services;
    }
}
