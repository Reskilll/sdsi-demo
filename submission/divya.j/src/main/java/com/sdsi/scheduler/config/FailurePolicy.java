package com.sdsi.scheduler.config;

/**
 * Policy governing running jobs when a failure event occurs.
 */
public enum FailurePolicy {
    /**
     * Currently running jobs are permitted to finish; only downstream dependents are skipped.
     */
    RUN_TO_COMPLETION,

    /**
     * Running jobs are immediately aborted when a failure is triggered.
     */
    CANCEL_IMMEDIATELY
}
