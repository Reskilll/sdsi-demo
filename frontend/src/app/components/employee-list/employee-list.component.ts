import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EmployeeService } from '../../services/employee.service';
import { AuthService } from '../../services/auth.service';
import { Employee, EmployeeStats } from '../../models/employee.model';
import { EmployeeFormComponent } from '../employee-form/employee-form.component';
import { environment } from '../../../environments/environment';

@Component({
  standalone: true,
  selector: 'app-employee-list',
  imports: [CommonModule, FormsModule, EmployeeFormComponent],
  templateUrl: './employee-list.component.html',
})
export class EmployeeListComponent implements OnInit {
  employees: Employee[] = [];
  filteredEmployees: Employee[] = [];
  searchQuery = '';
  selectedDepartment = '';
  departments: string[] = [];
  isLoading = false;
  showForm = false;
  editingEmployee: Employee | null = null;
  stats: EmployeeStats | null = null;

  // Pagination
  currentPage = 1;
  pageSize = 10;

  constructor(
    private employeeService: EmployeeService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadEmployees();
    this.loadStats();
  }

  get currentUser() {
    return this.authService.getCurrentUser();
  }

  get isAdmin() {
    return this.authService.isAdmin();
  }

  loadEmployees(): void {
    this.isLoading = true;
    this.employeeService.getAll().subscribe({
      next: (data) => {
        this.employees = data;
        this.departments = [...new Set(data.map((e) => e.department))];
        this.applyFilters();
        this.isLoading = false;
      },
      error: () => (this.isLoading = false),
    });
  }

  applyFilters(): void {
    let data = this.employees;

    if (this.searchQuery.trim()) {
      const q = this.searchQuery.toLowerCase();
      data = data.filter(
        (e) =>
          e.firstName.toLowerCase().includes(q) ||
          e.lastName.toLowerCase().includes(q) ||
          e.email.toLowerCase().includes(q) ||
          e.position.toLowerCase().includes(q)
      );
    }

    if (this.selectedDepartment) {
      data = data.filter((e) => e.department === this.selectedDepartment);
    }

    this.filteredEmployees = data;
    this.currentPage = 1;
  }

  get totalPages(): number {
    return Math.ceil(this.filteredEmployees.length / this.pageSize);
  }

  get paginatedEmployees(): Employee[] {
    const start = (this.currentPage - 1) * this.pageSize;
    return this.filteredEmployees.slice(start, start + this.pageSize);
  }

  changePage(page: number): void {
    this.currentPage = Math.max(1, Math.min(page, this.totalPages));
  }

  getPageNumbers(): number[] {
    const total = this.totalPages;
    if (total <= 5) return Array.from({ length: total }, (_, i) => i + 1);

    const pages: number[] = [1];
    const start = Math.max(2, this.currentPage - 1);
    const end = Math.min(total - 1, this.currentPage + 1);

    if (start > 2) pages.push(-1); // ellipsis
    for (let i = start; i <= end; i++) pages.push(i);
    if (end < total - 1) pages.push(-1);
    pages.push(total);

    return pages;
  }

  openCreate(): void {
    this.editingEmployee = null;
    this.showForm = true;
  }

  openEdit(employee: Employee): void {
    this.editingEmployee = { ...employee };
    this.showForm = true;
  }

  onFormSaved(): void {
    this.showForm = false;
    this.editingEmployee = null;
    this.loadEmployees();
  }

  onFormCancelled(): void {
    this.showForm = false;
    this.editingEmployee = null;
  }

  deleteEmployee(emp: Employee): void {
    if (!confirm(`Delete ${emp.firstName} ${emp.lastName}?`)) return;

    this.employeeService.delete(emp.id!).subscribe({
      next: () => {
        emp.isActive = false;
        this.applyFilters();
      },
      error: (err) => alert(err.error?.message || 'Delete failed'),
    });
  }

  reactivateEmployee(emp: Employee): void {
    this.employeeService.reactivate(emp.id!).subscribe({
      next: (updated) => {
        const idx = this.employees.findIndex((e) => e.id === emp.id);
        if (idx >= 0) this.employees[idx] = updated;
        this.applyFilters();
      },
      error: (err) => alert(err.error?.message || 'Reactivate failed'),
    });
  }

  logout(): void {
    this.authService.logout();
    this.router.navigate(['/login']);
  }

  // --- vishal.02 additions: Export & Dashboard ---

  loadStats(): void {
    this.employeeService.getStats().subscribe({
      next: (s) => (this.stats = s),
      error: () => {},
    });
  }

  exportCsv(): void {
    window.open(`${environment.apiUrl}/export/employees/csv`, '_blank');
  }
}