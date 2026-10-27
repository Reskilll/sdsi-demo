package com.sdsi.booking.web.error;

import com.sdsi.booking.web.dto.ConflictView;
import com.sdsi.booking.web.dto.OccurrenceView;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.dao.CannotAcquireLockException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.PessimisticLockingFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.net.URI;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Maps every failure to RFC 9457 problem+json. Internal details (stack traces,
 * SQL) never reach the client; unexpected errors are logged with the request id.
 */
@RestControllerAdvice
@org.springframework.core.annotation.Order(org.springframework.core.Ordered.HIGHEST_PRECEDENCE)
public class ApiExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(ApiExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ProblemDetail> handleApiException(ApiException ex, HttpServletRequest request) {
        ProblemDetail problem = problem(ex.getStatus(), ex.getMessage(), ex.getCode(), request);
        if (ex instanceof BookingConflictException conflict) {
            problem.setProperty("conflicts", conflict.getConflicts());
        } else if (ex instanceof RecurringConflictException recurring) {
            List<OccurrenceView> conflicting = recurring.getOccurrences().stream()
                    .filter(o -> !o.conflicts().isEmpty())
                    .toList();
            problem.setProperty("occurrences", conflicting);
            problem.setProperty("conflictCount", conflicting.size());
            problem.setProperty("totalOccurrences", recurring.getOccurrences().size());
        }
        return respond(ex.getStatus(), problem);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> handleValidation(MethodArgumentNotValidException ex,
                                                          HttpServletRequest request) {
        List<Map<String, String>> errors = new ArrayList<>();
        for (FieldError error : ex.getBindingResult().getFieldErrors()) {
            errors.add(fieldError(error.getField(), error.getDefaultMessage()));
        }
        ex.getBindingResult().getGlobalErrors()
                .forEach(error -> errors.add(fieldError("_request", error.getDefaultMessage())));

        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST, "Request validation failed.",
                "VALIDATION_FAILED", request);
        problem.setProperty("errors", errors);
        return respond(HttpStatus.BAD_REQUEST, problem);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ProblemDetail> handleConstraintViolation(ConstraintViolationException ex,
                                                                   HttpServletRequest request) {
        List<Map<String, String>> errors = ex.getConstraintViolations().stream()
                .map(v -> fieldError(lastNode(v.getPropertyPath().toString()), v.getMessage()))
                .toList();
        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST, "Request validation failed.",
                "VALIDATION_FAILED", request);
        problem.setProperty("errors", errors);
        return respond(HttpStatus.BAD_REQUEST, problem);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ProblemDetail> handleUnreadable(HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST,
                "Request body is missing or malformed. Check field types and ISO-8601 date/time formats.",
                "INVALID_JSON", request);
        return respond(HttpStatus.BAD_REQUEST, problem);
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<ProblemDetail> handleMissingParameter(MissingServletRequestParameterException ex,
                                                                 HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST,
                "Required query parameter '" + ex.getParameterName() + "' is missing.",
                "MISSING_PARAMETER", request);
        return respond(HttpStatus.BAD_REQUEST, problem);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ProblemDetail> handleTypeMismatch(MethodArgumentTypeMismatchException ex,
                                                            HttpServletRequest request) {
        String expected = ex.getRequiredType() == null ? "the expected type" : ex.getRequiredType().getSimpleName();
        ProblemDetail problem = problem(HttpStatus.BAD_REQUEST,
                "Parameter '" + ex.getName() + "' has an invalid value; expected " + expected + ".",
                "INVALID_PARAMETER", request);
        return respond(HttpStatus.BAD_REQUEST, problem);
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ProblemDetail> handleMethodNotSupported(HttpRequestMethodNotSupportedException ex,
                                                                  HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.METHOD_NOT_ALLOWED,
                "HTTP method " + ex.getMethod() + " is not supported for this resource.",
                "METHOD_NOT_ALLOWED", request);
        return respond(HttpStatus.METHOD_NOT_ALLOWED, problem);
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ProblemDetail> handleMediaType(HttpMediaTypeNotSupportedException ex,
                                                         HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.UNSUPPORTED_MEDIA_TYPE,
                "Content-Type must be application/json.", "UNSUPPORTED_MEDIA_TYPE", request);
        return respond(HttpStatus.UNSUPPORTED_MEDIA_TYPE, problem);
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ProblemDetail> handleNoResource(HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.NOT_FOUND,
                "The requested resource does not exist.", "NOT_FOUND", request);
        return respond(HttpStatus.NOT_FOUND, problem);
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ResponseEntity<ProblemDetail> handleDataIntegrity(DataIntegrityViolationException ex,
                                                             HttpServletRequest request) {
        log.warn("Data integrity violation on {}: {}", request.getRequestURI(), ex.getMostSpecificCause().getMessage());
        ProblemDetail problem = problem(HttpStatus.CONFLICT,
                "The change conflicts with stored data.", "DATA_INTEGRITY", request);
        return respond(HttpStatus.CONFLICT, problem);
    }

    @ExceptionHandler({PessimisticLockingFailureException.class, CannotAcquireLockException.class})
    public ResponseEntity<ProblemDetail> handleLocking(Exception ex, HttpServletRequest request) {
        log.warn("Lock contention on {}: {}", request.getRequestURI(), ex.getMessage());
        ProblemDetail problem = problem(HttpStatus.CONFLICT,
                "The room is being modified concurrently. Please retry.", "CONCURRENT_MODIFICATION", request);
        return respond(HttpStatus.CONFLICT, problem);
    }

    @ExceptionHandler(org.springframework.orm.ObjectOptimisticLockingFailureException.class)
    public ResponseEntity<ProblemDetail> handleOptimisticLock(
            org.springframework.orm.ObjectOptimisticLockingFailureException ex, HttpServletRequest request) {
        ProblemDetail problem = problem(HttpStatus.CONFLICT,
                "The booking was modified concurrently. Reload and try again.", "STALE_VERSION", request);
        return respond(HttpStatus.CONFLICT, problem);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ProblemDetail> handleUnexpected(Exception ex, HttpServletRequest request) {
        log.error("Unhandled error on {} {}", request.getMethod(), request.getRequestURI(), ex);
        ProblemDetail problem = problem(HttpStatus.INTERNAL_SERVER_ERROR,
                "An unexpected error occurred. Quote the request id when contacting support.",
                "INTERNAL_ERROR", request);
        return respond(HttpStatus.INTERNAL_SERVER_ERROR, problem);
    }

    private static ProblemDetail problem(HttpStatus status, String detail, String code, HttpServletRequest request) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(status, detail);
        problem.setTitle(status.getReasonPhrase());
        problem.setType(URI.create("about:blank"));
        problem.setInstance(URI.create(request.getRequestURI()));
        problem.setProperty("code", code);
        problem.setProperty("timestamp", Instant.now());
        String requestId = MDC.get("requestId");
        if (requestId != null) {
            problem.setProperty("requestId", requestId);
        }
        return problem;
    }

    private static ResponseEntity<ProblemDetail> respond(HttpStatus status, ProblemDetail problem) {
        return ResponseEntity.status(status)
                .contentType(MediaType.APPLICATION_PROBLEM_JSON)
                .body(problem);
    }

    private static Map<String, String> fieldError(String field, String message) {
        Map<String, String> error = new LinkedHashMap<>();
        error.put("field", field);
        error.put("message", message == null ? "invalid value" : message);
        return error;
    }

    private static String lastNode(String path) {
        int index = path.lastIndexOf('.');
        return index >= 0 ? path.substring(index + 1) : path;
    }
}
