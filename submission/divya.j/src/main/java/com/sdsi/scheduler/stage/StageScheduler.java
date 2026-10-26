package com.sdsi.scheduler.stage;

import com.sdsi.scheduler.model.*;

import java.util.*;

/**
 * Milestone 3: Group jobs into parallel execution stages with a configurable worker limit N,
 * and provide discrete-event timeline simulation.
 */
public class StageScheduler {

    /**
     * Groups jobs into parallel stages such that:
     * 1. No job runs before all its dependencies have completed in earlier stages.
     * 2. No stage contains more than 'workerLimit' jobs.
     *
     * @param graph       The job DAG
     * @param workerLimit Maximum workers (N >= 1)
     * @return List of Stage instances
     */
    public List<Stage> groupIntoStages(JobGraph graph, int workerLimit) {
        if (workerLimit < 1) {
            throw new IllegalArgumentException("Worker limit must be >= 1, received: " + workerLimit);
        }
        if (graph == null || graph.isEmpty()) {
            return Collections.emptyList();
        }

        Map<String, Integer> inDegree = new HashMap<>();
        for (String id : graph.getAllJobIds()) {
            inDegree.put(id, graph.getInDegree(id));
        }

        List<String> currentReady = new ArrayList<>();
        for (Map.Entry<String, Integer> entry : inDegree.entrySet()) {
            if (entry.getValue() == 0) {
                currentReady.add(entry.getKey());
            }
        }
        Collections.sort(currentReady);

        List<Stage> stages = new ArrayList<>();
        int stageCounter = 1;

        while (!currentReady.isEmpty()) {
            // Partition current wave into batches of size <= workerLimit
            List<String> nextReady = new ArrayList<>();
            int index = 0;

            while (index < currentReady.size()) {
                int batchEnd = Math.min(index + workerLimit, currentReady.size());
                List<String> batchJobs = new ArrayList<>(currentReady.subList(index, batchEnd));

                long maxDuration = 0L;
                for (String jId : batchJobs) {
                    Job j = graph.getJob(jId);
                    if (j != null && j.getDuration() > maxDuration) {
                        maxDuration = j.getDuration();
                    }
                }

                stages.add(new Stage(stageCounter++, batchJobs, maxDuration));
                index = batchEnd;
            }

            // After current wave finishes, resolve next ready jobs
            for (String completedJob : currentReady) {
                for (String dependent : graph.getDependents(completedJob)) {
                    int remaining = inDegree.get(dependent) - 1;
                    inDegree.put(dependent, remaining);
                    if (remaining == 0) {
                        nextReady.add(dependent);
                    }
                }
            }
            Collections.sort(nextReady);
            currentReady = nextReady;
        }

        return Collections.unmodifiableList(stages);
    }

    /**
     * Discrete-event simulation of dynamic asynchronous scheduling across N workers.
     * As soon as any worker becomes free, it picks the next available ready job.
     */
    public SimulationReport simulateExecution(JobGraph graph, int workerLimit) {
        if (workerLimit < 1) {
            throw new IllegalArgumentException("Worker limit must be >= 1, received: " + workerLimit);
        }
        if (graph == null || graph.isEmpty()) {
            return new SimulationReport(workerLimit, Collections.emptyList(), 0L);
        }

        Map<String, Integer> remainingPrereqs = new HashMap<>();
        for (String id : graph.getAllJobIds()) {
            remainingPrereqs.put(id, graph.getInDegree(id));
        }

        PriorityQueue<String> readyQueue = new PriorityQueue<>();
        for (Map.Entry<String, Integer> entry : remainingPrereqs.entrySet()) {
            if (entry.getValue() == 0) {
                readyQueue.offer(entry.getKey());
            }
        }

        PriorityQueue<Integer> availableWorkers = new PriorityQueue<>();
        for (int i = 1; i <= workerLimit; i++) {
            availableWorkers.offer(i);
        }

        // Completion event queue ordered by timestamp, then worker ID
        PriorityQueue<TaskCompletionEvent> eventQueue = new PriorityQueue<>(
                Comparator.comparingLong(TaskCompletionEvent::getFinishTime)
                        .thenComparingInt(TaskCompletionEvent::getWorkerId)
        );

        List<ScheduledTask> scheduledTasks = new ArrayList<>();
        long currentTime = 0;
        int completedCount = 0;
        int totalJobs = graph.size();

        while (completedCount < totalJobs) {
            // Assign available ready jobs to available workers
            while (!readyQueue.isEmpty() && !availableWorkers.isEmpty()) {
                String jobId = readyQueue.poll();
                int workerId = availableWorkers.poll();
                Job job = graph.getJob(jobId);
                long duration = (job != null) ? job.getDuration() : 0L;
                long finishTime = currentTime + duration;

                scheduledTasks.add(new ScheduledTask(jobId, workerId, currentTime, finishTime, duration));
                eventQueue.offer(new TaskCompletionEvent(finishTime, jobId, workerId));
            }

            if (eventQueue.isEmpty()) {
                break; // No more active tasks
            }

            // Advance time to next completion event
            TaskCompletionEvent nextEvent = eventQueue.poll();
            currentTime = nextEvent.getFinishTime();
            completedCount++;
            availableWorkers.offer(nextEvent.getWorkerId());

            // Process all events happening at this exact timestamp
            List<TaskCompletionEvent> sameTimeEvents = new ArrayList<>();
            sameTimeEvents.add(nextEvent);
            while (!eventQueue.isEmpty() && eventQueue.peek().getFinishTime() == currentTime) {
                TaskCompletionEvent ev = eventQueue.poll();
                completedCount++;
                availableWorkers.offer(ev.getWorkerId());
                sameTimeEvents.add(ev);
            }

            // For all completed jobs at this timestamp, unlock downstream dependents
            for (TaskCompletionEvent ev : sameTimeEvents) {
                for (String dep : graph.getDependents(ev.getJobId())) {
                    int rem = remainingPrereqs.get(dep) - 1;
                    remainingPrereqs.put(dep, rem);
                    if (rem == 0) {
                        readyQueue.offer(dep);
                    }
                }
            }
        }

        // Sort scheduled tasks by startTime, then workerId for clean output
        scheduledTasks.sort(Comparator.comparingLong(ScheduledTask::getStartTime)
                .thenComparingInt(ScheduledTask::getWorkerId));

        return new SimulationReport(workerLimit, scheduledTasks, currentTime);
    }

    private static class TaskCompletionEvent {
        private final long finishTime;
        private final String jobId;
        private final int workerId;

        public TaskCompletionEvent(long finishTime, String jobId, int workerId) {
            this.finishTime = finishTime;
            this.jobId = jobId;
            this.workerId = workerId;
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
    }
}
