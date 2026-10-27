package com.sds.ebc.dto;

import java.time.LocalDateTime;
import java.util.List;

public record OpportunityDTO(
    String id, String leaderId, Long clientId, String clientName,
    String source, String businessModel, String pricing,
    String procurementDept, Double valueLakh, String title,
    String status, Integer stage, String competitor,
    LocalDateTime createdAt, LocalDateTime closeDate,
    LocalDateTime expectedClose, LocalDateTime dueDate,
    Integer cycleDays, String lesson, Double winProbability,
    List<String> reasons
) {}
