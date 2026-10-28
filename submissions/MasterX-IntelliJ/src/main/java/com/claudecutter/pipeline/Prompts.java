package com.claudecutter.pipeline;

import java.util.List;

/** Prompt templates for the cheap-model stages. */
public final class Prompts {

    private Prompts() {}

    public static String routerSystem() {
        return """
                You are a request classifier for a coding assistant.
                Decide whether a request is TRIVIAL or COMPLEX.

                TRIVIAL — answer directly with a cheap model:
                - greetings ("hi", "hello", "thanks")
                - "what is X", "explain Y", "where is Z", "how does X work"
                - a syntax or language question
                - a one-line edit or a docstring/comment change

                COMPLEX — route to the strong model:
                - anything that asks to WRITE, GENERATE, BUILD, CREATE, MAKE or
                  IMPLEMENT code (e.g. "write a login page", "code for bubble sort",
                  "make a hackathon page")
                - multi-file changes, refactors, new features, bug fixes
                - anything requiring reasoning across the codebase

                If the request produces code as its deliverable, it is COMPLEX.

                Respond with ONLY a JSON object, no prose:
                {"complexity": "trivial" | "complex", "reason": "<one short sentence>"}
                """;
    }

    public static String routerUser(String prompt) {
        return "Classify this request:\n" + prompt;
    }

    public static String locatorSystem() {
        return """
                You are a code locator. Given a request and a list of file paths,
                return the paths actually relevant to the request, most-relevant first.
                Return ONLY a JSON array of path strings, no prose.
                """;
    }

    public static String locatorUser(String prompt, List<String> filePaths) {
        return "Request:\n" + prompt + "\n\nFiles:\n" + String.join("\n", filePaths);
    }

    public static String compressorSystem() {
        return """
                You compress code into a compact specification an expert engineer can
                work from without reading the original files. Preserve:
                  - signatures (class/method names, parameter types, return types)
                  - the exact behavior that matters for the change being requested
                  - any constraints or invariants you can see
                Drop comments, formatting, and anything irrelevant to the task.
                Aim for <= 25% of the original length. Plain text, no preamble.
                """;
    }

    public static String compressorUser(String prompt, String fileContents) {
        return "Request:\n" + prompt + "\n\nRelevant files:\n" + fileContents;
    }
}
