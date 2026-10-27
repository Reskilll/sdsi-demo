package com.sdsi.splitsmart.controller;

import com.sdsi.splitsmart.dto.BatchRequest;
import com.sdsi.splitsmart.dto.ExpenseRequest;
import com.sdsi.splitsmart.dto.GroupSnapshot;
import com.sdsi.splitsmart.service.SplitService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class SplitController {

    private final SplitService service;

    public SplitController(SplitService service) {
        this.service = service;
    }

    /** M1: Add a single expense. */
    @PostMapping("/expense")
    public ResponseEntity<GroupSnapshot> addExpense(
            @RequestBody ExpenseRequest request) {
        try {
            GroupSnapshot snapshot = service.addExpense(request);
            return ResponseEntity.ok(snapshot);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest()
                    .body(new GroupSnapshot(null, null));
        }
    }

    /** M4: Add a batch of expenses. */
    @PostMapping("/expenses/batch")
    public ResponseEntity<GroupSnapshot> addBatch(
            @RequestBody BatchRequest request) {
        try {
            GroupSnapshot snapshot = service.addBatch(request.expenses());
            return ResponseEntity.ok(snapshot);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest()
                    .body(new GroupSnapshot(null, null));
        }
    }

    /** M2 + M3: View current balances and settlements. */
    @GetMapping("/snapshot")
    public ResponseEntity<GroupSnapshot> getSnapshot() {
        return ResponseEntity.ok(service.getSnapshot());
    }

    /** Reset all data. */
    @PostMapping("/reset")
    public ResponseEntity<GroupSnapshot> reset() {
        return ResponseEntity.ok(service.reset());
    }

    /** Error handler returns validation details. */
    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<Map<String, String>> handleValidation(IllegalArgumentException ex) {
        return ResponseEntity.badRequest().body(Map.of("error", ex.getMessage()));
    }
}