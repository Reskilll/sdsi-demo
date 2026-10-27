package com.sds.ebc.dto;

import java.util.List;

public record BidCheckResult(
    double winProbability, double margin, double expectedValue,
    double presalesCost, String verdict, List<String> issues,
    List<SkillGap> skillGaps, List<FactorInfo> factors
) {}
