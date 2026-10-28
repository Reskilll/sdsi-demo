package com.claudecutter.model;

/** Router output: is this trivial (Qwen handles it) or complex (needs Claude)? */
public record RouteDecision(Complexity complexity, String reason) {

    public enum Complexity { TRIVIAL, COMPLEX }

    /** Which model answers the request. */
    public String target() {
        return complexity == Complexity.TRIVIAL ? "qwen" : "claude";
    }
}
