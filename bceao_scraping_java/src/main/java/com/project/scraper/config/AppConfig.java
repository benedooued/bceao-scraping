package main.java.com.project.scraper.config;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

//a declaration used to create a special, concise type of class designed to hold immutable data

public record AppConfig(
    String baseUrl,
    String homeUrl,
    Path outputDir,
    List<String> knownCountries,
    int annualStartYear,
    int annualEndYear,
    MonthYear monthlyStart,
    MonthYear monthlyEnd,
    String metadata,
    boolean verifySsl
) {

    // Nested record representing (Month, Year) tuples cleanly
    public record MonthYear(String month, int year) {}

    // Default configuration preset mirroring your Python values
    public static AppConfig defaultConfig() {
        String base = "https://edenpub.bceao.int/";
        Path exportDir = Paths.get("exports_bceao");
        
        // Ensure directory exists on initialization
        try {
            Files.createDirectories(exportDir);
        } catch (Exception e) {
            throw new RuntimeException("Failed to create output directory: " + exportDir, e);
        }

        return new AppConfig(
            base,
            URI.create(base).resolve("rapportPredefini.php").toString(),
            exportDir,
            List.of("B", "C", "A", "S", "D", "H", "K", "T", "Z"),
            2020,
            2026,
            new MonthYear("01", 2020),
            new MonthYear("12", 2025),
            "1",
            false // SSL verification flag
        );
    }
}