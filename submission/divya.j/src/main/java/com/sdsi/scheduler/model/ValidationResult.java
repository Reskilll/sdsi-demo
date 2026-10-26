package com.sdsi.scheduler.model;

import java.util.*;

/**
 * Structured validation report for Milestone 1.
 */
public class ValidationResult {

    private final boolean valid;
    private final Map<String, List<String>> missingDependencies;  // jobId -> missing prereqs
    private final Map<String, List<String>> duplicateDependencies;// jobId -> duplicate prereqs
    private final List<List<String>> detectedCycles;              // formatted cycle paths
    private final List<String> validationErrors;                  // general integrity errors

    public ValidationResult(
            boolean valid,
            Map<String, List<String>> missingDependencies,
            Map<String, List<String>> duplicateDependencies,
            List<List<String>> detectedCycles,
            List<String> validationErrors
    ) {
        this.valid = valid;
        this.missingDependencies = missingDependencies != null ? Collections.unmodifiableMap(missingDependencies) : Collections.emptyMap();
        this.duplicateDependencies = duplicateDependencies != null ? Collections.unmodifiableMap(duplicateDependencies) : Collections.emptyMap();
        this.detectedCycles = detectedCycles != null ? Collections.unmodifiableList(detectedCycles) : Collections.emptyList();
        this.validationErrors = validationErrors != null ? Collections.unmodifiableList(validationErrors) : Collections.emptyList();
    }

    public static ValidationResult valid() {
        return new ValidationResult(true, Collections.emptyMap(), Collections.emptyMap(), Collections.emptyList(), Collections.emptyList());
    }

    public boolean isValid() {
        return valid;
    }

    public boolean hasMissingDependencies() {
        return !missingDependencies.isEmpty();
    }

    public boolean hasDuplicateDependencies() {
        return !duplicateDependencies.isEmpty();
    }

    public boolean hasCycles() {
        return !detectedCycles.isEmpty();
    }

    public Map<String, List<String>> getMissingDependencies() {
        return missingDependencies;
    }

    public Map<String, List<String>> getDuplicateDependencies() {
        return duplicateDependencies;
    }

    public List<List<String>> getDetectedCycles() {
        return detectedCycles;
    }

    public List<String> getValidationErrors() {
        return validationErrors;
    }

    @Override
    public String toString() {
        if (valid) {
            return "ValidationResult: Valid DAG (No cycles, all dependencies resolved, durations valid).";
        }
        StringBuilder sb = new StringBuilder("ValidationResult: FAILED\n");
        if (!validationErrors.isEmpty()) {
            sb.append("  Validation Errors:\n");
            for (String err : validationErrors) {
                sb.append("   - ").append(err).append("\n");
            }
        }
        if (hasDuplicateDependencies()) {
            sb.append("  Duplicate Dependency References:\n");
            for (Map.Entry<String, List<String>> entry : duplicateDependencies.entrySet()) {
                sb.append("   - Job '").append(entry.getKey())
                        .append("' contains duplicate dependencies: ").append(entry.getValue()).append("\n");
            }
        }
        if (hasMissingDependencies()) {
            sb.append("  Missing Dependencies:\n");
            for (Map.Entry<String, List<String>> entry : missingDependencies.entrySet()) {
                sb.append("   - Job '").append(entry.getKey())
                        .append("' depends on non-existent job(s): ").append(entry.getValue()).append("\n");
            }
        }
        if (hasCycles()) {
            sb.append("  Detected Directed Cycles:\n");
            for (List<String> cycle : detectedCycles) {
                sb.append("   - ").append(String.join(" -> ", cycle)).append("\n");
            }
        }
        return sb.toString().trim();
    }
}
