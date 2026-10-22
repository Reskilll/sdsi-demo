import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  standalone: true,
  selector: 'app-login',
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
})
export class LoginComponent implements OnInit {
  loginForm!: FormGroup;
  registerForm!: FormGroup;
  isRegistering = false;
  errorMessage = '';
  isLoading = false;

  constructor(
    private authService: AuthService,
    private fb: FormBuilder,
    private router: Router
  ) {}

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.router.navigate(['/employees']);
      return;
    }

    this.loginForm = this.fb.group({
      username: ['', Validators.required],
      password: ['', Validators.required],
    });

    this.registerForm = this.fb.group({
      username: ['', [Validators.required, Validators.minLength(3)]],
      password: ['', [Validators.required, Validators.minLength(6)]],
      fullName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
    });
  }

  onLogin(): void {
    if (this.loginForm.invalid) return;

    this.errorMessage = '';
    this.isLoading = true;

    this.authService.login(this.loginForm.value).subscribe({
      next: () => this.router.navigate(['/employees']),
      error: (err) => {
        this.errorMessage = err.error?.message || 'Invalid username or password';
        this.isLoading = false;
      },
    });
  }

  onRegister(): void {
    if (this.registerForm.invalid) return;

    this.errorMessage = '';
    this.isLoading = true;

    this.authService.register(this.registerForm.value).subscribe({
      next: () => this.router.navigate(['/employees']),
      error: (err) => {
        this.errorMessage = err.error?.message || 'Registration failed';
        this.isLoading = false;
      },
    });
  }

  toggleMode(): void {
    this.isRegistering = !this.isRegistering;
    this.errorMessage = '';
  }
}