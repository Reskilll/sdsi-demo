package com.sdsi.scheduler.parser;

import com.sdsi.scheduler.config.SecurityLimits;
import com.sdsi.scheduler.model.Job;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.List;

/**
 * Standard parser delegating to hardened InputReader.
 */
public class JobJsonParser {

    private final InputReader inputReader;

    public JobJsonParser() {
        this.inputReader = new InputReader(new SecurityLimits());
    }

    public JobJsonParser(SecurityLimits securityLimits) {
        this.inputReader = new InputReader(securityLimits);
    }

    public List<Job> parseFromFile(File file) throws IOException {
        return inputReader.readFromFile(file, false);
    }

    public List<Job> parseFromFile(Path path) throws IOException {
        return inputReader.readFromFile(path.toFile(), false);
    }

    public List<Job> parseFromStream(InputStream inputStream) throws IOException {
        return inputReader.read(new String(inputStream.readAllBytes()), false);
    }

    public List<Job> parse(String json) throws IOException {
        return inputReader.read(json, false);
    }

    public List<Job> parseStrict(String json) throws IOException {
        return inputReader.read(json, true);
    }
}
