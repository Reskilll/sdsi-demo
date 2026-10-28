import { useQuery } from '@tanstack/react-query';
import { api } from './client';

export function useOverview() {
  return useQuery({ queryKey: ['overview'], queryFn: () => api.overview() });
}

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: () => api.projects() });
}

export function useProject(id: number) {
  return useQuery({ queryKey: ['project', id], queryFn: () => api.project(id) });
}

export function useDeveloper(projectId: number, userId: number) {
  return useQuery({ queryKey: ['developer', projectId, userId], queryFn: () => api.developer(projectId, userId) });
}

export function useMyUsage() {
  return useQuery({ queryKey: ['meUsage'], queryFn: () => api.myUsage() });
}

export function useModels() {
  return useQuery({ queryKey: ['models'], queryFn: () => api.models() });
}

export function useAdminUsers() {
  return useQuery({ queryKey: ['adminUsers'], queryFn: () => api.adminUsers() });
}

export function useAdminProjects() {
  return useQuery({ queryKey: ['adminProjects'], queryFn: () => api.adminProjects() });
}

export function useProjectMembers(projectId?: number) {
  return useQuery({
    queryKey: ['projectMembers', projectId],
    queryFn: () => api.projectMembers(projectId),
  });
}

export function useAudit() {
  return useQuery({ queryKey: ['audit'], queryFn: () => api.audit() });
}