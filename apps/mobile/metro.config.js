const http = require("node:http");

const { getDefaultConfig } = require("expo/metro-config");

const config = getDefaultConfig(__dirname);
const proxyPrefix = "/__hairdoc_api";
const backendOrigin = new URL(process.env.HAIRDOC_DEV_BACKEND_ORIGIN || "http://127.0.0.1:8000");
const previousEnhanceMiddleware = config.server?.enhanceMiddleware;

function proxyApiRequest(request, response) {
  const requestPath = request.url.slice(proxyPrefix.length) || "/";
  const target = new URL(requestPath, backendOrigin);

  if (!target.pathname.startsWith("/api/v1/")) {
    response.writeHead(404, { "Content-Type": "application/json" });
    response.end(JSON.stringify({ error: { code: "NOT_FOUND", message: "Development API route not found." } }));
    return;
  }

  const headers = { ...request.headers, host: backendOrigin.host };
  delete headers.connection;

  const upstream = http.request(
    {
      hostname: backendOrigin.hostname,
      port: backendOrigin.port || 80,
      method: request.method,
      path: `${target.pathname}${target.search}`,
      headers,
    },
    (upstreamResponse) => {
      const responseHeaders = { ...upstreamResponse.headers };
      delete responseHeaders.connection;
      response.writeHead(upstreamResponse.statusCode || 502, responseHeaders);
      upstreamResponse.pipe(response);
    },
  );

  upstream.on("error", () => {
    if (!response.headersSent) {
      response.writeHead(502, { "Content-Type": "application/json" });
    }
    response.end(JSON.stringify({ error: { code: "BACKEND_UNAVAILABLE", message: "The local backend is not running." } }));
  });

  request.pipe(upstream);
}

config.server = {
  ...config.server,
  enhanceMiddleware: (metroMiddleware, metroServer) => {
    const downstream = previousEnhanceMiddleware
      ? previousEnhanceMiddleware(metroMiddleware, metroServer)
      : metroMiddleware;

    return (request, response, next) => {
      if (request.url?.startsWith(proxyPrefix)) {
        proxyApiRequest(request, response);
        return;
      }
      downstream(request, response, next);
    };
  },
};

module.exports = config;
