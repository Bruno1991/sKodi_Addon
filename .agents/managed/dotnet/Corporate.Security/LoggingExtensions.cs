using Microsoft.Extensions.Logging;

namespace Corporate.Security;

public static class LoggingExtensions
{
    public static ILoggingBuilder AddCorporateJsonConsole(this ILoggingBuilder builder)
    {
        ArgumentNullException.ThrowIfNull(builder);
        builder.AddJsonConsole(options =>
        {
            options.IncludeScopes = true;
            options.TimestampFormat = "O";
            options.UseUtcTimestamp = true;
        });
        return builder;
    }
}
