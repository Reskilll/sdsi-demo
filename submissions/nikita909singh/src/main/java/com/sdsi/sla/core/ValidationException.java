package com.sdsi.sla.core;

import java.util.List;

/** Invalid input. Carries every problem found, not just the first, so all can be fixed at once. */
public class ValidationException extends RuntimeException {

    private final List<String> errors;

    public ValidationException(List<String> errors) {
        super(String.join("; ", errors));
        this.errors = List.copyOf(errors);
    }

    public ValidationException(String error) {
        this(List.of(error));
    }

    public List<String> errors() {
        return errors;
    }
}
