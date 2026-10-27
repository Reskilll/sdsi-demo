package com.sdsi.scheduler.parser;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sdsi.scheduler.config.SecurityLimits;
import com.sdsi.scheduler.model.Job;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Hardened JSON input parser enforcing resource bounds and strict schema validation.
 */
public class InputReader {

    private final ObjectMapper strictMapper;
    private final ObjectMapper permissiveMapper;
    private final SecurityLimits securityLimits;

    public InputReader() {
        this(new SecurityLimits());
    }

    public InputReader(SecurityLimits securityLimits) {
        this.securityLimits = Objects.requireNonNull(securityLimits, "securityLimits cannot be null");

        // Strict mapper: fails on unknown properties
        this.strictMapper = new ObjectMapper()
                .enable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION);

        // Permissive mapper for backward compatibility mode if explicitly enabled
        this.permissiveMapper = new ObjectMapper()
                .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION);
    }

    public List<Job> readFromFile(File file, boolean strictSchema) throws IOException {
        if (file == null || !file.exists()) {
            throw new IllegalArgumentException("JSON file does not exist: " + (file != null ? file.getPath() : "null"));
        }
        if (file.length() > securityLimits.getMaxFileSizeBytes()) {
            throw new IllegalArgumentException("File size (" + file.length() + " bytes) exceeds maximum security limit ("
                    + securityLimits.getMaxFileSizeBytes() + " bytes).");
        }
        return read(Files.readString(file.toPath()), strictSchema);
    }

    public List<Job> read(String json, boolean strictSchema) throws IOException {
        if (json == null || json.trim().isEmpty()) {
            return Collections.emptyList();
        }

        if (json.length() > securityLimits.getMaxFileSizeBytes()) {
            throw new IllegalArgumentException("JSON payload length exceeds maximum security limit.");
        }

        ObjectMapper mapper = strictSchema ? strictMapper : permissiveMapper;
        JsonNode root = mapper.readTree(json);

        if (root == null || root.isNull()) {
            return Collections.emptyList();
        }

        if (root.isArray()) {
            return parseArrayNode(root, mapper);
        }

        if (root.isObject() && root.has("jobs") && root.get("jobs").isArray()) {
            return parseArrayNode(root.get("jobs"), mapper);
        }

        if (root.isObject()) {
            return parseMapNode(root);
        }

        throw new IllegalArgumentException("Unsupported JSON root format. Expected array or object.");
    }

    private List<Job> parseArrayNode(JsonNode arrayNode, ObjectMapper mapper) throws IOException {
        if (arrayNode.size() > securityLimits.getMaxJobCount()) {
            throw new IllegalArgumentException("Job count (" + arrayNode.size() + ") exceeds security maximum ("
                    + securityLimits.getMaxJobCount() + ").");
        }

        List<Job> jobs = new ArrayList<>(arrayNode.size());
        Set<String> seenIds = new HashSet<>(arrayNode.size());
        int totalDependencies = 0;

        for (JsonNode element : arrayNode) {
            Job job = mapper.treeToValue(element, Job.class);
            if (job == null || job.getId() == null || job.getId().trim().isEmpty()) {
                throw new IllegalArgumentException("Job definition must contain a non-null, non-blank ID.");
            }
            if (!seenIds.add(job.getId())) {
                throw new IllegalArgumentException("Duplicate job ID detected: '" + job.getId() + "'");
            }
            totalDependencies += job.getDependsOn().size();
            if (totalDependencies > securityLimits.getMaxDependenciesCount()) {
                throw new IllegalArgumentException("Total dependencies count exceeds maximum security limit ("
                        + securityLimits.getMaxDependenciesCount() + ").");
            }
            jobs.add(job);
        }
        return jobs;
    }

    private List<Job> parseMapNode(JsonNode root) {
        if (root.size() > securityLimits.getMaxJobCount()) {
            throw new IllegalArgumentException("Job count exceeds security limit.");
        }

        List<Job> jobs = new ArrayList<>(root.size());
        Iterator<Map.Entry<String, JsonNode>> fields = root.fields();
        int totalDeps = 0;

        while (fields.hasNext()) {
            Map.Entry<String, JsonNode> entry = fields.next();
            String jobId = entry.getKey();
            if (jobId == null || jobId.trim().isEmpty()) {
                throw new IllegalArgumentException("Job ID in map key cannot be null or blank.");
            }

            JsonNode valNode = entry.getValue();
            if (!valNode.isObject()) {
                throw new IllegalArgumentException("Expected object value for job '" + jobId + "'");
            }

            long duration = 0L;
            if (valNode.has("duration")) {
                duration = valNode.get("duration").asLong(0L);
            } else if (valNode.has("time")) {
                duration = valNode.get("time").asLong(0L);
            }

            List<String> dependsOn = new ArrayList<>();
            JsonNode depsNode = valNode.has("dependsOn") ? valNode.get("dependsOn") : valNode.get("dependencies");
            if (depsNode != null && depsNode.isArray()) {
                for (JsonNode d : depsNode) {
                    if (d != null && !d.asText().trim().isEmpty()) {
                        dependsOn.add(d.asText().trim());
                    }
                }
            }

            totalDeps += dependsOn.size();
            if (totalDeps > securityLimits.getMaxDependenciesCount()) {
                throw new IllegalArgumentException("Total dependencies count exceeds security limit.");
            }

            jobs.add(new Job(jobId, duration, dependsOn));
        }

        return jobs;
    }
}
