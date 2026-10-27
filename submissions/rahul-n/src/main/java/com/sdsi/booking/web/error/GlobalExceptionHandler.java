package com.sdsi.booking.web.error;

import com.fasterxml.jackson.databind.exc.InvalidFormatException;
import com.sdsi.booking.web.dto.BookingDtos;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;

import java.util.List;

/** Translates domain and framework failures into a single {@link BookingDtos.ApiError} shape. */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<BookingDtos.ApiError> handleApi(ApiException ex, HttpServletRequest request) {
        return ResponseEntity.status(ex.getStatus()).body(BookingDtos.ApiError.of(
                ex.getStatus().value(),
                ex.getStatus().getReasonPhrase(),
                ex.getMessage(),
                request.getRequestURI(),
                ex.getDetails()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<BookingDtos.ApiError> handleValidation(MethodArgumentNotValidException ex,
                                                                HttpServletRequest request) {
        List<String> details = ex.getBindingResult().getFieldErrors().stream()
                .map(GlobalExceptionHandler::describe)
                .sorted()
                .toList();
        return ResponseEntity.badRequest().body(BookingDtos.ApiError.of(
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "request validation failed",
                request.getRequestURI(),
                details));
    }

    @ExceptionHandler({MissingServletRequestParameterException.class, MethodArgumentTypeMismatchException.class})
    public ResponseEntity<BookingDtos.ApiError> handleBadParameter(Exception ex, HttpServletRequest request) {
        return ResponseEntity.badRequest().body(BookingDtos.ApiError.of(
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                ex.getMessage(),
                request.getRequestURI(),
                List.of()));
    }

    /** Unparseable JSON bodies and malformed timestamps are client errors, not 500s. */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<BookingDtos.ApiError> handleUnreadableBody(HttpMessageNotReadableException ex,
                                                                    HttpServletRequest request) {
        InvalidFormatException invalid = findInvalidFormat(ex);
        List<String> details = invalid == null ? List.of() : describeInvalidFormats(invalid);
        return ResponseEntity.badRequest().body(BookingDtos.ApiError.of(
                HttpStatus.BAD_REQUEST.value(),
                HttpStatus.BAD_REQUEST.getReasonPhrase(),
                "request body is malformed or contains an invalid value",
                request.getRequestURI(),
                details));
    }

    /** Jackson nests the useful exception, so walk the chain instead of trusting one level. */
    private static InvalidFormatException findInvalidFormat(Throwable thrown) {
        for (Throwable current = thrown; current != null; current = current.getCause()) {
            if (current instanceof InvalidFormatException invalid) {
                return invalid;
            }
        }
        return null;
    }

    private static List<String> describeInvalidFormats(InvalidFormatException invalid) {
        String target = invalid.getTargetType() == null ? "value" : invalid.getTargetType().getSimpleName();
        if (invalid.getPath().isEmpty()) {
            return List.of("value '%s' is not a valid %s".formatted(invalid.getValue(), target));
        }
        return invalid.getPath().stream()
                .map(ref -> "%s: value '%s' is not a valid %s".formatted(ref.getFieldName(), invalid.getValue(), target))
                .distinct()
                .toList();
    }

    /**
     * Last-ditch guard: if a constraint is violated despite the pessimistic lock, surface
     * it as a conflict rather than a generic 500.
     */
    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<BookingDtos.ApiError> handleIntegrityViolation(DataIntegrityViolationException ex,
                                                                        HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(BookingDtos.ApiError.of(
                HttpStatus.CONFLICT.value(),
                HttpStatus.CONFLICT.getReasonPhrase(),
                "the request violates a data constraint (the slot may have just been taken)",
                request.getRequestURI(),
                List.of()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<BookingDtos.ApiError> handleUnexpected(Exception ex, HttpServletRequest request) {
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(BookingDtos.ApiError.of(
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                HttpStatus.INTERNAL_SERVER_ERROR.getReasonPhrase(),
                "unexpected error: " + ex.getClass().getSimpleName(),
                request.getRequestURI(),
                List.of()));
    }

    private static String describe(FieldError error) {
        return "%s: %s".formatted(error.getField(), error.getDefaultMessage());
    }
}
