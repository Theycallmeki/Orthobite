import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import App from './App.vue'
import router from './router'
import theme from './theme'

const app = createApp(App)
app.use(createPinia())
app.use(PrimeVue, {
  theme: {
    preset: theme,
    options: {
      darkModeSelector: false,
      cssLayer: {
        name: 'primevue',
        order: 'theme, base, primevue, components, utilities',
      },
    },
  },
})
app.use(router)
app.mount('#app')
