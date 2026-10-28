package com.mesterx.dashboard.domain;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "model_prices")
public class ModelPrice {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "model_id", nullable = false)
    private Long modelId;

    @Column(name = "input_per_1k", nullable = false)
    private BigDecimal inputPer1k;

    @Column(name = "output_per_1k", nullable = false)
    private BigDecimal outputPer1k;

    @Column(name = "valid_from", nullable = false)
    private Instant validFrom;

    @Column(name = "valid_to")
    private Instant validTo;

    public Long getId() { return id; }
    public Long getModelId() { return modelId; }
    public void setModelId(Long modelId) { this.modelId = modelId; }
    public BigDecimal getInputPer1k() { return inputPer1k; }
    public void setInputPer1k(BigDecimal inputPer1k) { this.inputPer1k = inputPer1k; }
    public BigDecimal getOutputPer1k() { return outputPer1k; }
    public void setOutputPer1k(BigDecimal outputPer1k) { this.outputPer1k = outputPer1k; }
    public Instant getValidFrom() { return validFrom; }
    public void setValidFrom(Instant validFrom) { this.validFrom = validFrom; }
    public Instant getValidTo() { return validTo; }
    public void setValidTo(Instant validTo) { this.validTo = validTo; }
}
