import { MOCK } from './mock';
import type { AuditEntry, CurrentUser, Model, Overview, ProjectDetail, ProjectSummary, AdminUser, AdminProject, ProjectMemberRow } from './types';

/**
 * Fetches data from the backend API, or from mock data when
 * VITE_USE_MOCK === 'true' (set in .env for the demo build).
 */
const useMock = import.meta.env.VITE_USE_MOCK === 'true';

function delay<T>(value: T, ms = 220): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  });
  if (res.status === 401) {
    const err: Error & { status?: number } = new Error('Unauthorized');
    err.status = 401;
    throw err;
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.message ?? message;
    } catch {
      /* ignore */
    }
    const err: Error & { status?: number } = new Error(message);
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

export const api = {
  // auth
  login(email: string, _password: string): Promise<CurrentUser> {
    if (useMock) return delay(MOCK.currentUser('ADMIN'));
    return http('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password: _password }) });
  },
  logout(): Promise<void> {
    if (useMock) return delay(undefined);
    return http('/api/auth/logout', { method: 'POST' });
  },
  me(): Promise<CurrentUser> {
    if (useMock) return delay(MOCK.currentUser('ADMIN'));
    return http('/api/auth/me');
  },

  // dashboard
  overview(): Promise<Overview> {
    if (useMock) return delay(MOCK.overview());
    return http('/api/dashboard/overview');
  },

  // projects
  projects(): Promise<ProjectSummary[]> {
    if (useMock) return delay(MOCK.projectSummaries());
    return http('/api/projects');
  },
  project(id: number): Promise<ProjectDetail> {
    if (useMock) return delay(MOCK.projectDetail(id));
    return http(`/api/projects/${id}`);
  },
  developer(projectId: number, userId: number): Promise<import('./types').DeveloperDetail> {
    if (useMock) return delay(MOCK.developerDetail(projectId, userId));
    return http(`/api/projects/${projectId}/members/${userId}`);
  },
  myUsage(): Promise<import('./types').DeveloperDetail> {
    if (useMock) return delay(MOCK.meUsage());
    return http('/api/me/usage');
  },

  // models & admin
  models(): Promise<Model[]> {
    if (useMock) return delay(MOCK.models());
    return http('/api/models');
  },
  adminUsers(): Promise<AdminUser[]> {
    if (useMock) return delay(MOCK.adminUsers());
    return http('/api/admin/users');
  },
  adminProjects(): Promise<AdminProject[]> {
    if (useMock) return delay(MOCK.adminProjects());
    return http('/api/admin/projects');
  },
  projectMembers(projectId?: number): Promise<ProjectMemberRow[]> {
    if (useMock) return delay(MOCK.projectMembers(projectId));
    const query = projectId ? `?projectId=${projectId}` : '';
    return http(`/api/projects/members${query}`);
  },
  audit(): Promise<AuditEntry[]> {
    if (useMock) return delay(MOCK.audit());
    return http('/api/admin/audit');
  },
};