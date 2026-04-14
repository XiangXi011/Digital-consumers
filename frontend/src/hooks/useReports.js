import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';

export function useReports(params = {}) {
  return useQuery({
    queryKey: ['reports', params],
    queryFn: () => api.getReports(params),
    staleTime: 30_000,
  });
}

export function useReport(id) {
  return useQuery({
    queryKey: ['report', id],
    queryFn: () => api.getReport(id),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useShareReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => api.shareReport(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['report', id] });
    },
  });
}
