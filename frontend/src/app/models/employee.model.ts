export interface Employee {
  id?: number;
  firstName: string;
  lastName: string;
  email: string;
  phoneNumber?: string;
  department: string;
  position: string;
  salary?: number;
  hireDate?: string;
  isActive?: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  tokenType: string;
  username: string;
  fullName: string;
  email: string;
  role: string;
}

export interface RegisterRequest {
  username: string;
  password: string;
  fullName: string;
  email: string;
}