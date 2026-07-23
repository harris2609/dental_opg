import { createApp } from 'vue'
import { setConfig, frappeRequest } from 'frappe-ui'
import App from './App.vue'
import router from './router'
import './index.css'

const app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.mount('#app')
