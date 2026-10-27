module.exports = {
  devServer: {
    port: 8080,
    // Proxy API calls to the backend during development.
    proxy: {
      '^/api': {
        target: 'http://127.0.0.1:3000',
        changeOrigin: true,
      },
      '^/healthz': {
        target: 'http://127.0.0.1:3000',
        changeOrigin: true,
      },
    },
  },
  publicPath: './',
  outputDir: 'dist',
};