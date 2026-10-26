package com.sdsi.scheduler.config;

import com.sdsi.scheduler.policy.FifoPolicy;
import com.sdsi.scheduler.policy.SchedulingPolicy;

import java.util.Objects;

/**
 * Immutable configuration for the Job Scheduler execution engine.
 */
public class SchedulerConfig {

    private final int workerLimit;
    private final SchedulingPolicy schedulingPolicy;
    private final FailurePolicy failurePolicy;
    private final String simulatedFailureJobId;
    private final boolean allowZeroDuration;

    private SchedulerConfig(Builder builder) {
        if (builder.workerLimit < 1) {
            throw new IllegalArgumentException("Worker limit must be >= 1, received: " + builder.workerLimit);
        }
        this.workerLimit = builder.workerLimit;
        this.schedulingPolicy = Objects.requireNonNull(builder.schedulingPolicy, "schedulingPolicy cannot be null");
        this.failurePolicy = Objects.requireNonNull(builder.failurePolicy, "failurePolicy cannot be null");
        this.simulatedFailureJobId = builder.simulatedFailureJobId;
        this.allowZeroDuration = builder.allowZeroDuration;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static SchedulerConfig defaultConfig() {
        return builder().build();
    }

    public int getWorkerLimit() {
        return workerLimit;
    }

    public SchedulingPolicy getSchedulingPolicy() {
        return schedulingPolicy;
    }

    public FailurePolicy getFailurePolicy() {
        return failurePolicy;
    }

    public String getSimulatedFailureJobId() {
        return simulatedFailureJobId;
    }

    public boolean isAllowZeroDuration() {
        return allowZeroDuration;
    }

    public static class Builder {
        private int workerLimit = 2;
        private SchedulingPolicy schedulingPolicy = new FifoPolicy();
        private FailurePolicy failurePolicy = FailurePolicy.RUN_TO_COMPLETION;
        private String simulatedFailureJobId = null;
        private boolean allowZeroDuration = true;

        public Builder workerLimit(int workerLimit) {
            this.workerLimit = workerLimit;
            return this;
        }

        public Builder schedulingPolicy(SchedulingPolicy policy) {
            this.schedulingPolicy = policy;
            return this;
        }

        public Builder failurePolicy(FailurePolicy policy) {
            this.failurePolicy = policy;
            return this;
        }

        public Builder simulatedFailureJobId(String jobId) {
            this.simulatedFailureJobId = jobId;
            return this;
        }

        public Builder allowZeroDuration(boolean allow) {
            this.allowZeroDuration = allow;
            return this;
        }

        public SchedulerConfig build() {
            return new SchedulerConfig(this);
        }
    }
}
