package com.sdsi.scheduler.model;

import com.fasterxml.jackson.annotation.JsonAlias;
import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * Immutable definition of an executable job within the DAG.
 */
public class Job {

    private final String id;
    private final long duration;
    private final List<String> dependsOn;

    @JsonCreator
    public Job(
            @JsonProperty(value = "id", required = true) @JsonAlias({"name", "jobId", "key"}) String id,
            @JsonProperty(value = "duration", required = true) @JsonAlias({"time", "cost", "weight"}) Long duration,
            @JsonProperty("dependsOn") @JsonAlias({"dependencies", "deps", "parents"}) List<String> dependsOn
    ) {
        this.id = id != null ? id.trim() : null;
        this.duration = duration != null ? duration : 0L;
        if (dependsOn != null) {
            List<String> list = new ArrayList<>(dependsOn.size());
            for (String dep : dependsOn) {
                list.add(dep != null ? dep.trim() : null);
            }
            this.dependsOn = Collections.unmodifiableList(list);
        } else {
            this.dependsOn = Collections.emptyList();
        }
    }

    public String getId() {
        return id;
    }

    public long getDuration() {
        return duration;
    }

    public List<String> getDependsOn() {
        return dependsOn;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Job job = (Job) o;
        return Objects.equals(id, job.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }

    @Override
    public String toString() {
        return "Job{" +
                "id='" + id + '\'' +
                ", duration=" + duration +
                ", dependsOn=" + dependsOn +
                '}';
    }
}
