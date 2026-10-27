import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Pipeline from '../views/Pipeline.vue'
import BidCheck from '../views/BidCheck.vue'
import Learnings from '../views/Learnings.vue'

const routes = [
  { path: '/', name: 'dashboard', component: Dashboard },
  { path: '/pipeline', name: 'pipeline', component: Pipeline },
  { path: '/bid-check', name: 'bid-check', component: BidCheck },
  { path: '/learnings', name: 'learnings', component: Learnings }
]

export default createRouter({ history: createWebHistory(), routes })
