package main.java.com.project.scraper.scrapers;



import main.java.com.project.scraper.config.AppConfig;
import main.java.com.project.scraper.scrapers.model.FormField;
import main.java.com.project.scraper.scrapers.model.Report;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class ScraperService {

    // Regex parsing soumettreTab('freq', 'id', 'title')
    private static final Pattern ONCLICK_PATTERN = Pattern.compile(
        "soumettreTab\\(\\s*['\"]([^'\"]+)['\"]\\s*,\\s*['\"]([^'\"]+)['\"]\\s*,\\s*['\"]((?:\\\\.|[^'\"])*)['\"]"
    );

    private final AppConfig config;

    public ScraperService(AppConfig config) {
        this.config = config;
    }

    /**
     * Parses `onclick` JavaScript calls on the homepage to find available reports.
     */
    public List<Report> extractReports(String htmlContent) {
        Document homepage = Jsoup.parse(htmlContent);
        List<Report> reports = new ArrayList<>();
        Set<String> seenIds = new HashSet<>();

        Elements elements = homepage.select("*[onclick]");
        for (Element element : elements) {
            String onclick = element.attr("onclick");
            Matcher matcher = ONCLICK_PATTERN.matcher(onclick);

            if (!matcher.find()) {
                continue;
            }

            String frequency = matcher.group(1).trim();
            String reportId = matcher.group(2).trim();
            String rawTitle = matcher.group(3).trim();

            if (seenIds.contains(reportId)) {
                continue;
            }

            seenIds.add(reportId);

            // Clean escaped quotes inside JavaScript string literals
            String cleanedTitle = rawTitle.replace("\\'", "'");
            reports.add(new Report(frequency, reportId, cleanedTitle));
        }

        return reports;
    }

    /**
     * Detects available country checkbox values inside the report form.
     */
    public List<String> detectCountries(Element formElement) {
        Elements checkboxes = formElement.select("input[type=checkbox]");
        
        List<String> countries = checkboxes.stream()
            .map(cb -> cb.attr("value").trim())
            .filter(val -> !val.isEmpty())
            .distinct()
            .collect(Collectors.toList());

        if (countries.isEmpty()) {
            return new ArrayList<>(config.knownCountries());
        }

        return countries;
    }

    /**
     * Formats payload configuration string based on frequency and country list.
     */
    public String buildParams(String frequency, List<String> countries) {
        String countryString = String.join(";", countries);
        String dateStart;
        String dateEnd;

        if ("M".equalsIgnoreCase(frequency)) {
            AppConfig.MonthYear start = config.monthlyStart();
            AppConfig.MonthYear end = config.monthlyEnd();
            dateStart = String.format("%s;%d", start.month(), start.year());
            dateEnd = String.format("%s;%d", end.month(), end.year());
        } else if ("A".equalsIgnoreCase(frequency)) {
            dateStart = String.valueOf(config.annualStartYear());
            dateEnd = String.valueOf(config.annualEndYear());
        } else {
            throw new IllegalArgumentException("Fréquence non prise en charge : " + frequency);
        }

        return String.format("%s*%s*%s*%s*%s*l", frequency, countryString, dateStart, dateEnd, config.metadata());
    }

    /**
     * Extracts key-value FormField pairs from form inputs.
     */
    public List<FormField> serializeForm(Element formElement, List<String> targetCountries) {
        Set<String> countrySet = targetCountries == null ? Collections.emptySet() : new HashSet<>(targetCountries);
        List<FormField> payload = new ArrayList<>();

        Elements inputElements = formElement.select("input, select, textarea");

        for (Element element : inputElements) {
            String name = element.attr("name");
            if (name.isBlank()) {
                continue;
            }

            String tagName = element.tagName().toLowerCase();
            String inputType = element.attr("type").toLowerCase();

            if ("input".equals(tagName)) {
                if (List.of("submit", "button", "reset", "image").contains(inputType)) {
                    continue;
                }

                String value = element.attr("value");

                if ("checkbox".equals(inputType)) {
                    if (!countrySet.contains(value)) {
                        continue;
                    }
                } else if ("radio".equals(inputType)) {
                    if (!element.hasAttr("checked")) {
                        continue;
                    }
                }
                payload.add(new FormField(name, value));

            } else if ("select".equals(tagName)) {
                Element selectedOption = element.selectFirst("option[selected]");
                if (selectedOption == null) {
                    selectedOption = element.selectFirst("option");
                }
                if (selectedOption == null) {
                    continue;
                }
                String value = selectedOption.hasAttr("value") ? selectedOption.attr("value") : selectedOption.text().trim();
                payload.add(new FormField(name, value));

            } else { // textarea
                payload.add(new FormField(name, element.text()));
            }
        }

        return payload;
    }

    /**
     * Updates or appends a key-value pair in a list of FormFields.
     */
    public List<FormField> setPayloadValue(List<FormField> payload, String key, String value) {
        List<FormField> updated = payload.stream()
            .filter(field -> !field.name().equals(key))
            .collect(Collectors.toList());

        updated.add(new FormField(key, value));
        return updated;
    }
}