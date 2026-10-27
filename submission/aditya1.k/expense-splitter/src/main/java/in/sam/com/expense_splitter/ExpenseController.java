package in.sam.com.expense_splitter;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/expenses")
public class ExpenseController {

    /**
     * Request DTO for submitting a batch of expenses.
     */
    public static class ExpenseRequest {
        private List<String> members;
        private List<Expense> expenses;

        public List<String> getMembers() {
            return members;
        }

        public void setMembers(List<String> members) {
            this.members = members;
        }

        public List<Expense> getExpenses() {
            return expenses;
        }

        public void setExpenses(List<Expense> expenses) {
            this.expenses = expenses;
        }
    }

    /**
     * Response DTO containing balances and settlements.
     */
    public record ExpenseResponse(
            Map<String, BigDecimal> totalPaid,
            Map<String, BigDecimal> totalOwed,
            Map<String, BigDecimal> netBalances,
            List<DebtSimplifier.Settlement> settlements
    ) {}

    /**
     * POST /api/expenses
     * Processes a batch of expenses and returns the summary.
     */
    @PostMapping
    public ResponseEntity<ExpenseResponse> processExpenses(
            @RequestBody ExpenseRequest request) {

        if (request == null
                || request.getMembers() == null
                || request.getExpenses() == null) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "JSON must contain members and expenses arrays");
        }

        try {
            ExpenseService service =
                    new ExpenseService(request.getMembers());

            // Validate the entire batch before processing.
            for (Expense expense : request.getExpenses()) {
                service.validate(expense);
            }

            for (Expense expense : request.getExpenses()) {
                service.process(expense);
            }

            Map<String, BigDecimal> paid =
                    service.getTotalPaid();

            Map<String, BigDecimal> owed =
                    service.getTotalOwed();

            Map<String, BigDecimal> balances =
                    service.getNetBalances();

            List<DebtSimplifier.Settlement> settlements =
                    new DebtSimplifier().simplify(balances);

            ExpenseResponse response = new ExpenseResponse(
                    paid, owed, balances, settlements);

            return ResponseEntity.ok(response);

        } catch (IllegalArgumentException e) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    e.getMessage(), e);
        }
    }

    /**
     * GET /api/expenses/health
     * Basic endpoint to verify the controller is running.
     */
    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of(
                "status", "UP",
                "service", "Expense Splitter"
        );
    }
}
