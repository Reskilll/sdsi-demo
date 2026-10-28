package com.mesterx.dashboard.domain;

import jakarta.persistence.*;

@Entity
@Table(name = "llm_models")
public class LlmModel {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String name;

    @Column(nullable = false)
    private String provider;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private Enums.Tier tier;

    @Column(nullable = false)
    private boolean enabled = true;

    public Long getId() { return id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getProvider() { return provider; }
    public void setProvider(String provider) { this.provider = provider; }
    public Enums.Tier getTier() { return tier; }
    public void setTier(Enums.Tier tier) { this.tier = tier; }
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
}
