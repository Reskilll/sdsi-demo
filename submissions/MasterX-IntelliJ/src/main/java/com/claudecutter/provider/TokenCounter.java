package com.claudecutter.provider;

/** Counts tokens in a string for a target model. */
public interface TokenCounter {
    long count(String text);
}
