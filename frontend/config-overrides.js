const webpack = require('webpack');

module.exports = function override(config) {
  const fallback = config.resolve.fallback || {};
  Object.assign(fallback, {
    "http": require.resolve("stream-http"),
    "https": require.resolve("https-browserify"),
    "util": require.resolve("util/"),
    "url": require.resolve("url/"),
    "crypto": require.resolve("crypto-browserify"),
    "stream": require.resolve("stream-browserify"),
    "assert": require.resolve("assert/"),
    "zlib": require.resolve("browserify-zlib")
  });
  config.resolve.fallback = fallback;

  config.plugins = (config.plugins || []).concat([
    new webpack.ProvidePlugin({
      Buffer: ['buffer', 'Buffer']
    })
  ]);

  // Add process fallback
  fallback.process = require.resolve('process/browser');
  
  // Define specific process.env variables needed
  config.plugins.push(
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(process.env.NODE_ENV || 'development'),
      'process.env.REACT_APP_API_URL': JSON.stringify(process.env.REACT_APP_API_URL),
      'process.env.REACT_APP_WS_URL': JSON.stringify(process.env.REACT_APP_WS_URL)
    })
  );

  // Allow ngrok host
  config.devServer = {
    ...config.devServer,
    allowedHosts: 'all',
    disableHostCheck: true
  };

  return config;
}
