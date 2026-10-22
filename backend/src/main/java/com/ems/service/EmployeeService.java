package com.ems.service;

import com.ems.dto.EmployeeRequest;
import com.ems.dto.EmployeeResponse;
import com.ems.entity.Employee;
import com.ems.repository.EmployeeRepository;
import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ems.dto.EmployeeStats;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class EmployeeService {

    private static final Logger logger = LoggerFactory.getLogger(EmployeeService.class);
    private final EmployeeRepository employeeRepository;

    @Transactional(readOnly = true)
    public List<EmployeeResponse> getAllEmployees() {
        return employeeRepository.findAll()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<EmployeeResponse> getActiveEmployees() {
        return employeeRepository.findByIsActiveTrue()
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public EmployeeResponse getEmployeeById(Long id) {
        Employee employee = employeeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Employee not found with id: " + id));
        return toResponse(employee);
    }

    @Transactional(readOnly = true)
    public List<EmployeeResponse> searchEmployees(String query) {
        return employeeRepository
                .findByFirstNameContainingIgnoreCaseOrLastNameContainingIgnoreCase(query, query)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional(readOnly = true)
    public List<EmployeeResponse> getEmployeesByDepartment(String department) {
        return employeeRepository.findByDepartment(department)
                .stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public EmployeeResponse createEmployee(EmployeeRequest request) {
        if (employeeRepository.findByEmail(request.getEmail()).isPresent()) {
            throw new DataIntegrityViolationException("Email already exists: " + request.getEmail());
        }

        Employee employee = Employee.builder()
                .firstName(request.getFirstName())
                .lastName(request.getLastName())
                .email(request.getEmail())
                .phoneNumber(request.getPhoneNumber())
                .department(request.getDepartment())
                .position(request.getPosition())
                .salary(request.getSalary())
                .hireDate(request.getHireDate())
                .build();

        Employee saved = employeeRepository.save(employee);
        logger.info("Created employee: {} {} (id={})", saved.getFirstName(), saved.getLastName(), saved.getId());
        return toResponse(saved);
    }

    @Transactional
    public EmployeeResponse updateEmployee(Long id, EmployeeRequest request) {
        Employee employee = employeeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Employee not found with id: " + id));

        employeeRepository.findByEmail(request.getEmail())
                .ifPresent(existing -> {
                    if (!existing.getId().equals(id)) {
                        throw new DataIntegrityViolationException("Email already in use: " + request.getEmail());
                    }
                });

        employee.setFirstName(request.getFirstName());
        employee.setLastName(request.getLastName());
        employee.setEmail(request.getEmail());
        employee.setPhoneNumber(request.getPhoneNumber());
        employee.setDepartment(request.getDepartment());
        employee.setPosition(request.getPosition());
        employee.setSalary(request.getSalary());
        employee.setHireDate(request.getHireDate());

        Employee saved = employeeRepository.save(employee);
        logger.info("Updated employee: {} {} (id={})", saved.getFirstName(), saved.getLastName(), saved.getId());
        return toResponse(saved);
    }

    @Transactional
    public void deleteEmployee(Long id) {
        Employee employee = employeeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Employee not found with id: " + id));
        employee.setIsActive(false);
        employeeRepository.save(employee);
        logger.info("Deactivated employee: {} {} (id={})", employee.getFirstName(), employee.getLastName(), id);
    }

    @Transactional
    public void hardDeleteEmployee(Long id) {
        if (!employeeRepository.existsById(id)) {
            throw new EntityNotFoundException("Employee not found with id: " + id);
        }
        employeeRepository.deleteById(id);
        logger.info("Hard-deleted employee with id={}", id);
    }

    @Transactional
    public EmployeeResponse reactivateEmployee(Long id) {
        Employee employee = employeeRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Employee not found with id: " + id));
        employee.setIsActive(true);
        Employee saved = employeeRepository.save(employee);
        logger.info("Reactivated employee: {} {} (id={})", saved.getFirstName(), saved.getLastName(), id);
        return toResponse(saved);
    }

    private EmployeeResponse toResponse(Employee e) {
        return EmployeeResponse.builder()
                .id(e.getId())
                .firstName(e.getFirstName())
                .lastName(e.getLastName())
                .email(e.getEmail())
                .phoneNumber(e.getPhoneNumber())
                .department(e.getDepartment())
                .position(e.getPosition())
                .salary(e.getSalary())
                .hireDate(e.getHireDate())
                .isActive(e.getIsActive())
                .createdAt(e.getCreatedAt())
                .updatedAt(e.getUpdatedAt())
                .build();
    }

    // --- vishal.02 additions: Dashboard & Export support ---

    @Transactional(readOnly = true)
    public EmployeeStats getStats() {
        List<Employee> all = employeeRepository.findAll();
        long total = all.size();
        long active = all.stream().filter(Employee::getIsActive).count();

        Map<String, Long> deptCounts = all.stream()
                .collect(Collectors.groupingBy(Employee::getDepartment, Collectors.counting()));

        String topDept = deptCounts.entrySet().stream()
                .max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey)
                .orElse("N/A");

        return EmployeeStats.builder()
                .totalEmployees(total)
                .activeEmployees(active)
                .inactiveEmployees(total - active)
                .departmentCount(deptCounts.size())
                .topDepartment(topDept)
                .build();
    }

    @Transactional(readOnly = true)
    public List<String> getAllDepartments() {
        return employeeRepository.findAll().stream()
                .map(Employee::getDepartment)
                .distinct()
                .sorted()
                .toList();
    }
}