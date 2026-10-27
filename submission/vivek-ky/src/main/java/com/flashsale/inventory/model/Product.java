package com.flashsale.inventory.model;

import jakarta.persistence.*;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;
import java.math.BigDecimal;

/**
 * Represents a flash-sale product with stock counters and per-user quota.
 *
 * Invariant enforced at all times:
 *   totalStock == availableStock + reservedStock + soldStock
 */
@Entity
@Table(name = "products")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Product {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, unique = true, length = 64, updatable = false)
    private String sku;

    @NotBlank
    @Column(nullable = false)
    private String name;

    @Min(0)
    @Column(name = "total_stock", nullable = false)
    private int totalStock;

    @Min(0)
    @Column(name = "available_stock", nullable = false)
    private int availableStock;

    @Min(0)
    @Column(name = "reserved_stock", nullable = false)
    private int reservedStock;

    @Min(0)
    @Column(name = "sold_stock", nullable = false)
    private int soldStock;

    @Min(1)
    @Column(name = "max_per_user", nullable = false)
    private int maxPerUser;

    @NotNull
    @Column(nullable = false, precision = 10, scale = 2)
    private BigDecimal price;

    /**
     * Returns true if the inventory invariant holds.
     */
    @Transient
    public boolean isInvariantValid() {
        return totalStock == availableStock + reservedStock + soldStock;
    }

    @Version
    @Column(nullable = false)
    private Long version; // optimistic locking backup
}