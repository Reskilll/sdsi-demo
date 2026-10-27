import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8085/api' })

export default {
  getDashboard() { return api.get('/dashboard') },
  getOpportunities() { return api.get('/opportunities') },
  getPipeline() { return api.get('/pipeline') },
  getOpen() { return api.get('/opportunities/open') },
  createOpportunity(data) { return api.post('/opportunities', data) },
  advanceStage(id) { return api.post(`/opportunities/${id}/advance`) },
  closeOpportunity(id, data) { return api.post(`/opportunities/${id}/close`, data) },
  getBidCheck(data) { return api.post('/bid-check', data) },
  getHealth() { return api.get('/health') },
  getSourceStats() { return api.get('/stats/sources') }
}
