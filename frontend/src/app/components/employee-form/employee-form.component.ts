import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { EmployeeService } from '../../services/employee.service';
import { Employee } from '../../models/employee.model';

@Component({
  standalone: true,
  selector: 'app-employee-form',
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './employee-form.component.html',
})
export class EmployeeFormComponent implements OnInit {
  @Input() employee: Employee | null = null;
  @Output() saved = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  form!: FormGroup;
  isSubmitting = false;
  errorMessage = '';

  departments = [
    'Engineering',
    'Marketing',
    'Finance',
    'HR',
    'Sales',
    'Operations',
    'Legal',
    'IT',
  ];

  constructor(
    private employeeService: EmployeeService,
    private fb: FormBuilder
  ) {}

  ngOnInit(): void {
    this.form = this.fb.group({
      firstName: [this.employee?.firstName || '', Validators.required],
      lastName: [this.employee?.lastName || '', Validators.required],
      email: [this.employee?.email || '', [Validators.required, Validators.email]],
      phoneNumber: [this.employee?.phoneNumber || ''],
      department: [this.employee?.department || '', Validators.required],
      position: [this.employee?.position || '', Validators.required],
      salary: [this.employee?.salary || null],
      hireDate: [this.employee?.hireDate || ''],
    });
  }

  get isEditing(): boolean {
    return !!this.employee;
  }

  onSubmit(): void {
    if (this.form.invalid) return;

    this.isSubmitting = true;
    this.errorMessage = '';

    const payload: Employee = {
      ...this.form.value,
      salary: this.form.value.salary ? Number(this.form.value.salary) : null,
    };

    const request$ = this.isEditing
      ? this.employeeService.update(this.employee!.id!, payload)
      : this.employeeService.create(payload);

    request$.subscribe({
      next: () => {
        this.isSubmitting = false;
        this.saved.emit();
      },
      error: (err) => {
        this.errorMessage = err.error?.message || 'Operation failed';
        this.isSubmitting = false;
      },
    });
  }

  cancel(): void {
    this.cancelled.emit();
  }
}