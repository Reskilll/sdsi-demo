package com.sdsi.scheduler.model;

/**
 * Lifecycle states of a job within the scheduler.
 */
public enum JobStatus {
    PENDING,    // Waiting for prerequisite dependencies to complete
    READY,      // All prerequisites completed; queued for worker assignment
    RUNNING,    // Actively executing on an assigned worker
    COMPLETED,  // Finished successfully
    FAILED,     // Failed during execution
    SKIPPED     // Bypassed because one or more upstream prerequisites failed
}
