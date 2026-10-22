package com.ems.controller;

import com.ems.service.EmployeeService;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;
import java.io.PrintWriter;

@RestController
@RequestMapping("/api/export")
@RequiredArgsConstructor
public class ExportController {

    private final EmployeeService employeeService;

    @GetMapping("/employees/csv")
    @PreAuthorize("hasAnyRole('USER', 'ADMIN')")
    public void exportEmployeesCsv(HttpServletResponse response) throws IOException {
        response.setContentType("text/csv");
        response.setHeader(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=employees.csv");

        PrintWriter writer = response.getWriter();
        writer.println("ID,First Name,Last Name,Email,Phone,Department,Position,Salary,Hire Date,Active");
        employeeService.getAllEmployees().forEach(e -> {
            writer.printf("%d,%s,%s,%s,%s,%s,%s,%.2f,%s,%s%n",
                    e.getId(),
                    escapeCsv(e.getFirstName()),
                    escapeCsv(e.getLastName()),
                    escapeCsv(e.getEmail()),
                    escapeCsv(e.getPhoneNumber()),
                    escapeCsv(e.getDepartment()),
                    escapeCsv(e.getPosition()),
                    e.getSalary(),
                    e.getHireDate(),
                    e.getIsActive());
        });
        writer.flush();
    }

    private String escapeCsv(String value) {
        if (value == null) return "";
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}