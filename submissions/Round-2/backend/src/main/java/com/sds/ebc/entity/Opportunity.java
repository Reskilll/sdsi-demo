package com.sds.ebc.entity;

import jakarta.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "opportunities")
public class Opportunity {
    @Id
    private String id;
    @Column(name = "leader_id") private String leaderId;
    @Column(name = "client_id") private Long clientId;
    private String source;
    @Column(name = "business_model") private String businessModel;
    private String pricing;
    @Column(name = "procurement_dept") private String procurementDept;
    @Column(name = "value_lakh") private Double valueLakh;
    private String title;
    private String status = "open";
    private Integer stage = 0;
    private Integer reached = 0;
    private String competitor;
    @Column(name = "created_at") private LocalDateTime createdAt;
    @Column(name = "close_date") private LocalDateTime closeDate;
    @Column(name = "expected_close") private LocalDateTime expectedClose;
    @Column(name = "due_date") private LocalDateTime dueDate;
    @Column(name = "cycle_days") private Integer cycleDays = 90;
    @Column(name = "last_update") private LocalDateTime lastUpdate;
    @Column(columnDefinition = "TEXT") private String lesson;
    @Column(name = "win_probability") private Double winProbability;

    public Opportunity() {}
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getLeaderId() { return leaderId; }
    public void setLeaderId(String leaderId) { this.leaderId = leaderId; }
    public Long getClientId() { return clientId; }
    public void setClientId(Long clientId) { this.clientId = clientId; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public String getBusinessModel() { return businessModel; }
    public void setBusinessModel(String businessModel) { this.businessModel = businessModel; }
    public String getPricing() { return pricing; }
    public void setPricing(String pricing) { this.pricing = pricing; }
    public String getProcurementDept() { return procurementDept; }
    public void setProcurementDept(String procurementDept) { this.procurementDept = procurementDept; }
    public Double getValueLakh() { return valueLakh; }
    public void setValueLakh(Double valueLakh) { this.valueLakh = valueLakh; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getStage() { return stage; }
    public void setStage(Integer stage) { this.stage = stage; }
    public Integer getReached() { return reached; }
    public void setReached(Integer reached) { this.reached = reached; }
    public String getCompetitor() { return competitor; }
    public void setCompetitor(String competitor) { this.competitor = competitor; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
    public LocalDateTime getCloseDate() { return closeDate; }
    public void setCloseDate(LocalDateTime closeDate) { this.closeDate = closeDate; }
    public LocalDateTime getExpectedClose() { return expectedClose; }
    public void setExpectedClose(LocalDateTime expectedClose) { this.expectedClose = expectedClose; }
    public LocalDateTime getDueDate() { return dueDate; }
    public void setDueDate(LocalDateTime dueDate) { this.dueDate = dueDate; }
    public Integer getCycleDays() { return cycleDays; }
    public void setCycleDays(Integer cycleDays) { this.cycleDays = cycleDays; }
    public LocalDateTime getLastUpdate() { return lastUpdate; }
    public void setLastUpdate(LocalDateTime lastUpdate) { this.lastUpdate = lastUpdate; }
    public String getLesson() { return lesson; }
    public void setLesson(String lesson) { this.lesson = lesson; }
    public Double getWinProbability() { return winProbability; }
    public void setWinProbability(Double winProbability) { this.winProbability = winProbability; }
}
