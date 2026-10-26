package com.sdsi.scheduler.config;

/**
 * Enforces hard security limits on untrusted JSON inputs to prevent resource exhaustion attacks.
 */
public final class SecurityLimits {

    public static final long DEFAULT_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
    public static final int DEFAULT_MAX_JOB_COUNT = 50_000;
    public static final int DEFAULT_MAX_DEPENDENCIES_COUNT = 100_000;

    private final long maxFileSizeBytes;
    private final int maxJobCount;
    private final int maxDependenciesCount;

    public SecurityLimits() {
        this(DEFAULT_MAX_FILE_SIZE_BYTES, DEFAULT_MAX_JOB_COUNT, DEFAULT_MAX_DEPENDENCIES_COUNT);
    }

    public SecurityLimits(long maxFileSizeBytes, int maxJobCount, int maxDependenciesCount) {
        if (maxFileSizeBytes <= 0 || maxJobCount <= 0 || maxDependenciesCount <= 0) {
            throw new IllegalArgumentException("Security limits must be strictly positive.");
        }
        this.maxFileSizeBytes = maxFileSizeBytes;
        this.maxJobCount = maxJobCount;
        this.maxDependenciesCount = maxDependenciesCount;
    }

    public long getMaxFileSizeBytes() {
        return maxFileSizeBytes;
    }

    public int getMaxJobCount() {
        return maxJobCount;
    }

    public int getMaxDependenciesCount() {
        return maxDependenciesCount;
    }
}
