package com.ems.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class EmployeeStats {

    private long totalEmployees;
    private long activeEmployees;
    private long inactiveEmployees;
    private long departmentCount;
    private String topDepartment;
}