package com.ems.config;

import com.ems.entity.Employee;
import com.ems.entity.User;
import com.ems.repository.EmployeeRepository;
import com.ems.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.env.Environment;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;

@Component
@RequiredArgsConstructor
public class DataSeeder implements CommandLineRunner {

    private static final Logger logger = LoggerFactory.getLogger(DataSeeder.class);
    private final UserRepository userRepository;
    private final EmployeeRepository employeeRepository;
    private final PasswordEncoder passwordEncoder;
    private final Environment env;

    @Override
    public void run(String... args) {
        if (userRepository.count() == 0) {
            seedUsers();
        }
        if (employeeRepository.count() == 0) {
            seedEmployees();
        }
    }

    private void seedUsers() {
        String adminPass = env.getProperty("EMS_ADMIN_PASSWORD");
        String userPass = env.getProperty("EMS_USER_PASSWORD");

        if (adminPass == null || userPass == null) {
            logger.warn("Set EMS_ADMIN_PASSWORD and EMS_USER_PASSWORD env vars to seed users");
            return;
        }

        userRepository.save(User.builder()
                .username("admin")
                .passwordHash(passwordEncoder.encode(adminPass))
                .fullName("System Administrator")
                .email("admin@ems.com")
                .role(User.Role.ADMIN)
                .isActive(true)
                .build());

        userRepository.save(User.builder()
                .username("user")
                .passwordHash(passwordEncoder.encode(userPass))
                .fullName("Regular User")
                .email("user@ems.com")
                .role(User.Role.USER)
                .isActive(true)
                .build());

        logger.info("Seeded 2 default users (admin, user)");
    }

    private void seedEmployees() {
        employeeRepository.save(Employee.builder()
                .firstName("John").lastName("Doe")
                .email("john.doe@ems.com")
                .phoneNumber("+1-555-0101")
                .department("Engineering")
                .position("Senior Developer")
                .salary(new BigDecimal("95000.00"))
                .hireDate(LocalDate.of(2020, 3, 15))
                .build());

        employeeRepository.save(Employee.builder()
                .firstName("Jane").lastName("Smith")
                .email("jane.smith@ems.com")
                .phoneNumber("+1-555-0102")
                .department("Marketing")
                .position("Marketing Manager")
                .salary(new BigDecimal("85000.00"))
                .hireDate(LocalDate.of(2021, 6, 1))
                .build());

        employeeRepository.save(Employee.builder()
                .firstName("Robert").lastName("Johnson")
                .email("robert.j@ems.com")
                .phoneNumber("+1-555-0103")
                .department("Engineering")
                .position("Junior Developer")
                .salary(new BigDecimal("65000.00"))
                .hireDate(LocalDate.of(2023, 1, 10))
                .build());

        employeeRepository.save(Employee.builder()
                .firstName("Emily").lastName("Davis")
                .email("emily.d@ems.com")
                .phoneNumber("+1-555-0104")
                .department("HR")
                .position("HR Specialist")
                .salary(new BigDecimal("70000.00"))
                .hireDate(LocalDate.of(2022, 9, 20))
                .build());

        employeeRepository.save(Employee.builder()
                .firstName("Michael").lastName("Wilson")
                .email("michael.w@ems.com")
                .phoneNumber("+1-555-0105")
                .department("Finance")
                .position("Financial Analyst")
                .salary(new BigDecimal("80000.00"))
                .hireDate(LocalDate.of(2021, 11, 5))
                .build());

        logger.info("Seeded 5 sample employees");
    }
}