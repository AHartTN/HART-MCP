// using HART.MCP.Infrastructure.Persistence;
// using HART.MCP.Infrastructure.Data;
using Microsoft.AspNetCore.HttpOverrides;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace HART.MCP.API.Extensions;

public static class WebApplicationExtensions
{
    public static Task EnsureDatabaseCreatedAsync(this WebApplication app)
    {
        using var scope = app.Services.CreateScope();
        var logger = scope.ServiceProvider.GetRequiredService<ILogger<WebApplication>>();
        
        try
        {
            logger.LogInformation("Database initialization skipped - Infrastructure disabled");
            
            // Infrastructure services disabled due to API compatibility issues
            // var context = scope.ServiceProvider.GetRequiredService<ApplicationDbContext>();
            // var seeder = scope.ServiceProvider.GetRequiredService<DatabaseSeeder>();
            // await seeder.SeedAsync();
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "An error occurred during database initialization");
            throw;
        }
        
        return Task.CompletedTask;
    }

    public static WebApplication ConfigurePipeline(this WebApplication app, IWebHostEnvironment environment)
    {
        // Production middleware pipeline (order matters!)
        app.UseForwardedHeaders();
        
        if (environment.IsProduction())
        {
            app.UseHsts();
        }

        app.UseHttpsRedirection();
        app.UseResponseCompression();
        app.UseResponseCaching();

        // Security middleware
        app.UseSecurityHeaders();
        
        // Modern request logging (built into .NET 8)
        if (environment.IsDevelopment())
        {
            app.UseHttpLogging();
        }
        
        // Global error handling
        app.UseMiddleware<GlobalExceptionMiddleware>();
        
        // Rate limiting
        app.UseRateLimiter();

        // Authentication & Authorization
        app.UseAuthentication();
        app.UseAuthorization();

        // API Documentation (conditional)
        if (environment.IsDevelopment() || environment.IsStaging())
        {
            app.UseSwagger();
            app.UseSwaggerUI(c =>
            {
                c.SwaggerEndpoint("/swagger/v1/swagger.json", "HART-MCP API v1");
                c.RoutePrefix = "api/docs";
                c.DisplayRequestDuration();
                c.EnableDeepLinking();
                c.EnableFilter();
                c.EnableTryItOutByDefault();
            });
        }

        // API Controllers
        app.MapControllers();

        // Health checks with modern patterns
        app.MapHealthChecks("/health");
        app.MapHealthChecks("/health/ready");
        app.MapHealthChecks("/health/live");

        return app;
    }

    public static IApplicationBuilder UseSecurityHeaders(this IApplicationBuilder app)
    {
        return app.Use(async (context, next) =>
        {
            // Modern security headers
            context.Response.Headers.Append("X-Content-Type-Options", "nosniff");
            context.Response.Headers.Append("X-Frame-Options", "DENY");
            context.Response.Headers.Append("X-XSS-Protection", "1; mode=block");
            context.Response.Headers.Append("Referrer-Policy", "strict-origin-when-cross-origin");
            context.Response.Headers.Append("Permissions-Policy", "geolocation=(), microphone=(), camera=()");
            context.Response.Headers.Append("Content-Security-Policy", 
                "default-src 'self'; " +
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
                "style-src 'self' 'unsafe-inline'; " +
                "img-src 'self' data: https:; " +
                "connect-src 'self'; " +
                "font-src 'self'; " +
                "object-src 'none'; " +
                "media-src 'self'; " +
                "frame-src 'none';");

            // Remove server header
            context.Response.Headers.Remove("Server");
            
            await next();
        });
    }
}