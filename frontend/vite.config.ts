import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(async () => {
	const { default: frappeui } = await import('frappe-ui/vite')

	return {
		plugins: [
			frappeui({
				frontendRoute: '/dental_opg',
				jinjaBootData: true,
			}),
			vue(),
		],
		resolve: {
			alias: {
				'@': path.resolve(__dirname, 'src'),
			},
		},
	}
})
