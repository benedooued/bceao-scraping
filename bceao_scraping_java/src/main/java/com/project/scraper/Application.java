package main.java.com.project.scraper;

import main.java.com.project.scraper.client.HttpClientManager;
import main.java.com.project.scraper.config.AppConfig;
import main.java.com.project.scraper.scrapers.ScraperService;
import main.java.com.project.scraper.scrapers.model.FormField;
import main.java.com.project.scraper.scrapers.model.Report;
import main.java.com.project.scraper.storage.FileStorageService;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

public class Application {

    private final AppConfig config;
    private final HttpClientManager clientManager;
    private final ScraperService scraperService;
    private final FileStorageService storageService;

    public Application(AppConfig config) {
        this.config = config;
        this.clientManager = new HttpClientManager(config);
        this.scraperService = new ScraperService(config);
        this.storageService = new FileStorageService(config);
    }

    public static void main(String[] args) {
        AppConfig config = AppConfig.defaultConfig();
        Application app = new Application(config);
        app.run();
    }

    public void run() {
        System.out.println("Connecting to BCEAO portal...");

    
        List<Map<String, String>> successful = new ArrayList<>();
        List<Map<String, String>> failed = new ArrayList<>();  
    

        try {
            HttpRequest.Builder homeReq = HttpRequest.newBuilder()
                .uri(URI.create(config.homeUrl()))
                .GET();

            HttpResponse<String> homeResp = clientManager.sendWithRetry(homeReq);
            List<Report> reports = scraperService.extractReports(homeResp.body());

            for (int i = 0; i < reports.size(); i++) {
                Report report = reports.get(i);
                System.out.printf("%nProcessing [%d/%d]: %s%n", i + 1, reports.size(), report.title());

                try {
                    Path savedPath = processSingleReport(report);
                    System.out.println("  Success -> Saved to " + savedPath.toAbsolutePath());

                    successful.add(Map.of(
                        "frequency", report.frequency(),
                        "id_tab", report.idTab(),
                        "title", report.title(),
                        "file", savedPath.toString()
                    ));
                } catch (Exception e) {
                    System.err.println("  Failed -> " + e.getMessage());

                    failed.add(Map.of(
                        "frequency", report.frequency(),
                        "id_tab", report.idTab(),
                        "title", report.title(),
                        "error", e.getMessage() == null ? e.toString() : e.getMessage()
                    ));
                }

                Thread.sleep(2000);
            }

        } catch (Exception e) {
            System.err.println("Fatal execution error: " + e.getMessage());
        } finally {
            writeSummaryCsv(config.outputDir().resolve("successful_exports.csv"), successful, List.of("frequency", "id_tab", "title", "file"));
            writeSummaryCsv(config.outputDir().resolve("failed_exports.csv"), failed, List.of("frequency", "id_tab", "title", "error"));
        }
    }

    private Path processSingleReport(Report report) throws Exception {
        URI urlConfig = URI.create(config.baseUrl()).resolve("tableauPredefini.php");
        List<FormField> configPayload = List.of(
            new FormField("frequence", report.frequency()),
            new FormField("idTab", report.idTab()),
            new FormField("libelleTab", report.title())
        );

        HttpRequest.Builder configReq = HttpRequest.newBuilder()
            .uri(urlConfig)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .header("Referer", config.homeUrl())
            .POST(HttpRequest.BodyPublishers.ofString(encodeFormPayload(configPayload)));

        HttpResponse<String> respConfig = clientManager.sendWithRetry(configReq);
        Document reportPage = Jsoup.parse(respConfig.body());
        Element form = reportPage.selectFirst("form#form_consultation");

        if (form == null) {
            throw new IllegalStateException("form_consultation missing.");
        }

        List<String> countries = scraperService.detectCountries(form);
        String params = scraperService.buildParams(report.frequency(), countries);

        String action = form.hasAttr("action") && !form.attr("action").isBlank() 
            ? form.attr("action") 
            : "rapportPredefini.php";
            
        URI genUrl = URI.create(config.baseUrl()).resolve(action);
        List<FormField> payload = scraperService.serializeForm(form, countries);
        payload = scraperService.setPayloadValue(payload, "params", params);
        payload = scraperService.setPayloadValue(payload, "idTab", report.idTab());

        HttpRequest.Builder resultReq = HttpRequest.newBuilder()
            .uri(genUrl)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .header("Referer", genUrl.toString())
            .POST(HttpRequest.BodyPublishers.ofString(encodeFormPayload(payload)));

        HttpResponse<String> respResult = clientManager.sendWithRetry(resultReq);
        Document resultPage = Jsoup.parse(respResult.body());

        Elements forms = resultPage.select("form");
        Optional<Element> exportForm = forms.stream()
            .filter(f -> f.attr("action").toLowerCase().contains("export"))
            .findFirst();

        URI exportUrl;
        List<FormField> exportPayload;

        if (exportForm.isPresent()) {
            exportUrl = URI.create(config.baseUrl()).resolve(exportForm.get().attr("action"));
            exportPayload = scraperService.serializeForm(exportForm.get(), null);
        } else {
            exportUrl = URI.create(config.baseUrl()).resolve("exportTableauPredefiniEnColonne.php");
            exportPayload = new ArrayList<>();
        }

        exportPayload = scraperService.setPayloadValue(exportPayload, "params", params);
        exportPayload = scraperService.setPayloadValue(exportPayload, "idTab", report.idTab());
        exportPayload = scraperService.setPayloadValue(exportPayload, "export", "");

        HttpRequest.Builder fileReq = HttpRequest.newBuilder()
            .uri(exportUrl)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .header("Referer", config.homeUrl())
            .POST(HttpRequest.BodyPublishers.ofString(encodeFormPayload(exportPayload)));

        HttpResponse<byte[]> fileResp = clientManager.getClient().send(
            fileReq.build(), 
            HttpResponse.BodyHandlers.ofByteArray()
        );

        String contentType = fileResp.headers().firstValue("Content-Type").orElse("").toLowerCase();
        if (contentType.contains("html")) {
            throw new IllegalStateException("Server returned HTML page instead of expected data file.");
        }

        return storageService.saveReportFile(fileResp.body(), report.idTab(), report.title());
    }

    private String encodeFormPayload(List<FormField> fields) {
        return fields.stream()
            .map(field -> URLEncoder.encode(field.name(), StandardCharsets.UTF_8) + "=" +
                          URLEncoder.encode(field.value(), StandardCharsets.UTF_8))
            .collect(Collectors.joining("&"));
    }

    private void writeSummaryCsv(Path path,  List<Map<String, String>> records, List<String> headers) {
        try {
            List<String> lines = new ArrayList<>();
            lines.add(String.join(",", headers));

            for (Map<String, String> record : records) {
                String line = headers.stream()
                    .map(h -> "\"" + record.getOrDefault(h, "").replace("\"", "\"\"") + "\"")
                    .collect(Collectors.joining(","));
                lines.add(line);
            }

            Files.write(path, lines, StandardCharsets.UTF_8);
        } catch (Exception e) {
            System.err.println("Failed to write CSV summary report: " + e.getMessage());
        }
    }
}