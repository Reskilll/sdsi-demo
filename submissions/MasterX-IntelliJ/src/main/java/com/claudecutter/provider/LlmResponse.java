package com.claudecutter.provider;

import com.claudecutter.model.ModelUsage;

/** A single completed model turn. */
public record LlmResponse(String text, ModelUsage usage) {}
