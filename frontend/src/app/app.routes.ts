import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./components/login/login.component').then(m => m.LoginComponent) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: 'employees',
        loadComponent: () => import('./components/employee-list/employee-list.component').then(m => m.EmployeeListComponent),
      },
      { path: '', redirectTo: 'employees', pathMatch: 'full' },
    ],
  },
  { path: '**', redirectTo: 'employees' },
];