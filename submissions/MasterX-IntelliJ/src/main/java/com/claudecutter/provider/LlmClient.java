package com.claudecutter.provider;

/** Minimal LLM surface used by the pipeline. Implementations plug a provider. */
public interface LlmClient {
    String model();

    LlmResponse complete(String system, String user);
}
