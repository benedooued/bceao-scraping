package main.java.com.project.scraper.storage;


import main.java.com.project.scraper.config.AppConfig;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

/**
 * Service class responsible for saving report files to disk with proper extension detection and filename sanitization.
 */

public class FileStorageService {

    // Magic bytes detection signatures
    private static final byte[] PK_MAGIC = new byte[]{(byte) 0x50, (byte) 0x4B}; // ZIP / XLSX signature
    private static final byte[] OLE_MAGIC = new byte[]{(byte) 0xD0, (byte) 0xCF, (byte) 0x11, (byte) 0xE0}; // Legacy XLS signature

    private final Path outputDir;

    public FileStorageService(AppConfig config) {
        this.outputDir = config.outputDir();
    }

    /**
     * Inspects magic bytes and saves report binary content to disk with a safe filename.
     *
     * @param content  Raw binary payload of the report
     * @param reportId Unique identifier for the report
     * @param title    Original report title (will be sanitized for filesystem safety)
     * @return Path pointing to the written file
     * @throws IOException If file creation or writing fails
     */
    public Path saveReportFile(byte[] content, String reportId, String title) throws IOException {
        Files.createDirectories(outputDir);

        String extension = detectExtension(content);
        String safeTitle = sanitizeFilename(title);

        String filename = String.format("%s_%s%s", reportId, safeTitle, extension);
        Path filepath = outputDir.resolve(filename);

        Files.write(filepath, content);
        return filepath;
    }

    /**
     * Inspects the initial byte signature to determine the accurate extension (.xlsx, .xls, or .csv).
     */
    private String detectExtension(byte[] content) {
        if (content == null || content.length == 0) {
            return ".csv";
        }

        if (startsWithBytes(content, PK_MAGIC)) {
            return ".xlsx";
        } else if (startsWithBytes(content, OLE_MAGIC)) {
            return ".xls";
        }

        return ".csv";
    }

    private boolean startsWithBytes(byte[] content, byte[] prefix) {
        if (content.length < prefix.length) {
            return false;
        }
        byte[] targetHeader = Arrays.copyOfRange(content, 0, prefix.length);
        return Arrays.equals(targetHeader, prefix);
    }

    /**
     * Sanitizes string values into safe filesystem filenames by replacing invalid characters with underscores.
     */
    private String sanitizeFilename(String title) {
        if (title == null || title.isBlank()) {
            return "untitled";
        }
        return title.replaceAll("[<>:\"/\\\\|?*]+", "_");
    }
}