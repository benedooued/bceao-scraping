package main.java.com.project.scraper.client;


import main.java.com.project.scraper.config.AppConfig;

import java.io.IOException;
import java.net.CookieManager;
import java.net.CookiePolicy;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/**
 * Manages HTTP client configuration and request execution with retry logic.
 */

public class HttpClientManager {

    private static final String DEFAULT_USER_AGENT = 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36";

    private final HttpClient client;
    private final AppConfig config;

    public HttpClientManager(AppConfig config) {
        this.config = config;

        HttpClient.Builder builder = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(15))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .cookieHandler(new CookieManager(null, CookiePolicy.ACCEPT_ALL)); // Manages session cookies

        // Apply SSL configuration based on AppConfig
        if (!config.verifySsl()) {
            builder.sslContext(SslContextBuilder.createInsecureContext());
            // Disable hostname validation when SSL verification is off
            System.setProperty("jdk.internal.httpclient.disableHostnameVerification", "true");
        }

        this.client = builder.build();
    }

    /**
     * Executes an HTTP request with automatic retry logic (up to 3 attempts).
     *
     * @param requestBuilder Pre-configured HttpRequest.Builder target
     * @return Successful HttpResponse<String>
     */
    public HttpResponse<String> sendWithRetry(HttpRequest.Builder requestBuilder) throws IOException, InterruptedException {
        HttpRequest request = requestBuilder
            .header("User-Agent", DEFAULT_USER_AGENT)
            .timeout(Duration.ofSeconds(180)) // Read timeout (180s matching Python tuple)
            .build();

        int maxAttempts = 3;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try {
                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
                
                // Throw exception for 4xx/5xx status codes to trigger retry logic
                if (response.statusCode() >= 400) {
                    throw new IOException("HTTP request failed with status code: " + response.statusCode());
                }

                return response;

            } catch (IOException | InterruptedException e) {
                System.err.printf("  Tentative %d/%d échouée : %s%n", attempt, maxAttempts, e.getMessage());
                
                if (attempt == maxAttempts) {
                    throw e;
                }
                
                Thread.sleep(5000); // 5-second backoff delay matching Python time.sleep(5)
            }
        }

        throw new IOException("All retry attempts failed for URL: " + request.uri());
    }

    public HttpClient getClient() {
        return client;
    }
}