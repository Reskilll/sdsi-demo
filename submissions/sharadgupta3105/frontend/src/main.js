import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';
import ShortenView from './views/ShortenView.vue';
import StatsView from './views/StatsView.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ShortenView },
    { path: '/stats/:code', component: StatsView },
  ],
});

createApp(App).use(router).mount('#app');
