package com.sdsi.scheduler.engine;

import com.sdsi.scheduler.config.FailurePolicy;
import com.sdsi.scheduler.config.SchedulerConfig;
import com.sdsi.scheduler.cpm.CriticalPathAnalyzer;
import com.sdsi.scheduler.model.*;
import com.sdsi.scheduler.policy.SchedulingPolicy;
import com.sdsi.scheduler.stage.StageScheduler;

import java.util.*;

/**
 * Milestone 3: Discrete-Event Worker-Limited Parallel Scheduler.
 * Coordinates execution via an event-driven priority queue of completion timestamps.
 * Enforces worker concurrency limits, handles zero-time tasks, simultaneous completions,
 * and maintains strict separation across job lifecycle states.
 */
public class DiscreteEventScheduler {

    private final StageScheduler stageScheduler;
    private final CriticalPathAnalyzer cpmAnalyzer;
    private final FailurePropagator failurePropagator;

    public DiscreteEventScheduler() {
        this.stageScheduler = new StageScheduler();
        this.cpmAnalyzer = new CriticalPathAnalyzer();
        this.failurePropagator = new FailurePropagator();
    }

    public ScheduleResult schedule(JobGraph graph, SchedulerConfig config) {
        Objects.requireNonNull(graph, "graph cannot be null");
        Objects.requireNonNull(config, "config cannot be null");

        int workerLimit = config.getWorkerLimit();
        SchedulingPolicy policy = config.getSchedulingPolicy();
        String failedJobTrigger = config.getSimulatedFailureJobId();
        FailurePolicy failurePolicy = config.getFailurePolicy();

        if (graph.isEmpty()) {
            return new ScheduleResult(workerLimit, policy.getName(), 0L, 0L, 0.0,
                    Collections.emptyList(), Collections.emptyList(), Collections.emptyMap(), Collections.emptyList());
        }

        // 1. Compute baseline critical path makespan (theoretical lower bound)
        CriticalPathResult cpm = cpmAnalyzer.analyze(graph);
        long criticalPathLowerBound = cpm.getMinimumTotalCompletionTime();

        // 2. Compute barrier stages
        List<Stage> stages = stageScheduler.groupIntoStages(graph, workerLimit);

        // 3. Initialize state collections
        Map<String, JobExecutionState> states = new LinkedHashMap<>(graph.size());
        Map<String, Integer> remainingPrereqs = new HashMap<>(graph.size());

        for (String id : graph.getAllJobIds()) {
            states.put(id, new JobExecutionState(id));
            remainingPrereqs.put(id, graph.getInDegree(id));
        }

        // Ready queue ordered according to the selected SchedulingPolicy
        Comparator<String> policyComparator = policy.createComparator(graph);
        PriorityQueue<String> readyQueue = new PriorityQueue<>(policyComparator);

        // Pre-propagate skipped jobs if failure trigger is configured
        Set<String> preSkippedJobIds = new HashSet<>();
        if (failedJobTrigger != null && graph.containsJob(failedJobTrigger)) {
            FailureReport failReport = failurePropagator.propagateFailure(graph, failedJobTrigger);
            preSkippedJobIds.addAll(failReport.getAllSkippedJobs());

            for (String skippedId : failReport.getAllSkippedJobs()) {
                JobExecutionState s = states.get(skippedId);
                s.setStatus(JobStatus.SKIPPED);
                s.setReason(failReport.getSkipReasons().getOrDefault(skippedId, "Upstream prerequisite failed"));
            }
        }

        // Enqueue initially eligible root jobs
        for (Map.Entry<String, Integer> entry : remainingPrereqs.entrySet()) {
            String jobId = entry.getKey();
            if (entry.getValue() == 0 && !preSkippedJobIds.contains(jobId)) {
                states.get(jobId).setStatus(JobStatus.READY);
                readyQueue.offer(jobId);
            }
        }

        // Worker allocation pool (Worker 1 to Worker N)
        PriorityQueue<Integer> availableWorkers = new PriorityQueue<>();
        for (int i = 1; i <= workerLimit; i++) {
            availableWorkers.offer(i);
        }

        // Completion event queue ordered by finish timestamp, then worker ID, then job ID
        PriorityQueue<CompletionEvent> eventQueue = new PriorityQueue<>(
                Comparator.comparingLong(CompletionEvent::getFinishTime)
                        .thenComparingInt(CompletionEvent::getWorkerId)
                        .thenComparing(CompletionEvent::getJobId)
        );

        List<ScheduledTask> scheduledTasks = new ArrayList<>(graph.size());
        List<String> executionOrder = new ArrayList<>(graph.size());
        long currentTime = 0L;
        long totalBusyDuration = 0L;

        // Discrete-event simulation loop
        while (!readyQueue.isEmpty() || !eventQueue.isEmpty()) {

            // Step A: Assign available ready jobs to available workers at currentTime
            while (!readyQueue.isEmpty() && !availableWorkers.isEmpty()) {
                String jobId = readyQueue.poll();
                int workerId = availableWorkers.poll();

                Job job = graph.getJob(jobId);
                long duration = (job != null) ? job.getDuration() : 0L;
                long finishTime = Math.addExact(currentTime, duration);

                // Check if this job is the failure trigger
                boolean isFailedTrigger = jobId.equals(failedJobTrigger);

                JobExecutionState state = states.get(jobId);
                state.setStatus(JobStatus.RUNNING);
                state.setWorkerId(workerId);
                state.setStartTime(currentTime);

                scheduledTasks.add(new ScheduledTask(jobId, workerId, currentTime, finishTime, duration));
                eventQueue.offer(new CompletionEvent(finishTime, jobId, workerId, duration, isFailedTrigger));
            }

            if (eventQueue.isEmpty()) {
                break; // No running tasks and no ready tasks
            }

            // Step B: Advance clock to next earliest event timestamp
            CompletionEvent nextEvent = eventQueue.poll();
            currentTime = nextEvent.getFinishTime();

            // Collect all simultaneous completions happening at currentTime
            List<CompletionEvent> simultaneousEvents = new ArrayList<>();
            simultaneousEvents.add(nextEvent);

            while (!eventQueue.isEmpty() && eventQueue.peek().getFinishTime() == currentTime) {
                simultaneousEvents.add(eventQueue.poll());
            }

            // Step C: Process completions and release workers
            for (CompletionEvent ev : simultaneousEvents) {
                String completedJobId = ev.getJobId();
                int workerId = ev.getWorkerId();
                JobExecutionState state = states.get(completedJobId);
                state.setFinishTime(currentTime);

                if (ev.isFailed()) {
                    state.setStatus(JobStatus.FAILED);
                    state.setReason("Explicitly failed in simulation");
                    executionOrder.add(completedJobId + " [FAILED]");
                    availableWorkers.offer(workerId);

                    // If CANCEL_IMMEDIATELY, abort other running events
                    if (failurePolicy == FailurePolicy.CANCEL_IMMEDIATELY) {
                        while (!eventQueue.isEmpty()) {
                            CompletionEvent aborted = eventQueue.poll();
                            JobExecutionState abortedState = states.get(aborted.getJobId());
                            abortedState.setStatus(JobStatus.SKIPPED);
                            abortedState.setFinishTime(currentTime);
                            abortedState.setReason("Aborted immediately due to concurrent failure of '" + completedJobId + "'");
                            availableWorkers.offer(aborted.getWorkerId());
                        }
                        readyQueue.clear();
                    }
                    continue;
                }

                state.setStatus(JobStatus.COMPLETED);
                executionOrder.add(completedJobId);
                totalBusyDuration = Math.addExact(totalBusyDuration, ev.getDuration());
                availableWorkers.offer(workerId);

                // Unlock downstream dependents whose prerequisites are now satisfied
                for (String dependent : graph.getDependents(completedJobId)) {
                    if (preSkippedJobIds.contains(dependent)) {
                        continue;
                    }
                    int remaining = remainingPrereqs.get(dependent) - 1;
                    remainingPrereqs.put(dependent, remaining);
                    if (remaining == 0) {
                        JobExecutionState depState = states.get(dependent);
                        if (depState.getStatus() == JobStatus.PENDING) {
                            depState.setStatus(JobStatus.READY);
                            readyQueue.offer(dependent);
                        }
                    }
                }
            }
        }

        // Mark any remaining pending tasks as SKIPPED
        for (JobExecutionState s : states.values()) {
            if (s.getStatus() == JobStatus.PENDING) {
                s.setStatus(JobStatus.SKIPPED);
                s.setReason("Prerequisite dependencies were never satisfied");
            }
        }

        // Sort scheduled tasks by startTime, then workerId for clean deterministic output
        scheduledTasks.sort(Comparator.comparingLong(ScheduledTask::getStartTime)
                .thenComparingInt(ScheduledTask::getWorkerId));

        double workerUtilization = 0.0;
        long totalWorkerCapacity = (currentTime > 0) ? currentTime * (long) workerLimit : 0L;
        if (totalWorkerCapacity > 0) {
            workerUtilization = ((double) totalBusyDuration / (double) totalWorkerCapacity) * 100.0;
        }

        return new ScheduleResult(
                workerLimit,
                policy.getName(),
                currentTime,
                criticalPathLowerBound,
                workerUtilization,
                stages,
                scheduledTasks,
                states,
                executionOrder
        );
    }

    private static class CompletionEvent {
        private final long finishTime;
        private final String jobId;
        private final int workerId;
        private final long duration;
        private final boolean failed;

        public CompletionEvent(long finishTime, String jobId, int workerId, long duration, boolean failed) {
            this.finishTime = finishTime;
            this.jobId = jobId;
            this.workerId = workerId;
            this.duration = duration;
            this.failed = failed;
        }

        public long getFinishTime() {
            return finishTime;
        }

        public String getJobId() {
            return jobId;
        }

        public int getWorkerId() {
            return workerId;
        }

        public long getDuration() {
            return duration;
        }

        public boolean isFailed() {
            return failed;
        }
    }
}
