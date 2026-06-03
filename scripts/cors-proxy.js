#!/usr/bin/env node
/**
 * OpenCode CORS Proxy
 *
 * A minimal HTTP proxy that forwards requests to the OpenCode server
 * and adds CORS headers so the Acode plugin can connect from a
 * `file://` origin (Android WebView).
 *
 * This works around a bug in OpenCode v1.14.44 where `--cors "*"` does
 * not actually emit `Access-Control-Allow-Origin` headers.
 *
 * Usage:
 *   node scripts/cors-proxy.js [options]
 *
 * Options:
 *   --target-port PORT   OpenCode server port (default: 9876)
 *   --proxy-port  PORT   Proxy listen port (default: 9878)
 *   --host       HOST    Bind address (default: 127.0.0.1)
 */

"use strict";

var http = require("http");

// ─── Parse args ─────────────────────────────────────

var TARGET_PORT = 4096;
var PROXY_PORT = 9878;
var HOST = "127.0.0.1";

process.argv.slice(2).forEach(function (arg, i, args) {
  if (arg === "--target-port" && args[i + 1]) TARGET_PORT = parseInt(args[i + 1], 10);
  if (arg === "--proxy-port" && args[i + 1]) PROXY_PORT = parseInt(args[i + 1], 10);
  if (arg === "--host" && args[i + 1]) HOST = args[i + 1];
});

// ─── CORS headers ───────────────────────────────────

var CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept, X-Requested-With",
  "Access-Control-Expose-Headers": "Content-Type, Content-Length, X-Requested-With",
  "Access-Control-Max-Age": "86400",
};

// ─── Proxy server ───────────────────────────────────

var server = http.createServer(function (req, res) {
  // ── CORS preflight ─────────────────────────────
  if (req.method === "OPTIONS") {
    res.writeHead(204, CORS_HEADERS);
    return res.end();
  }

  // ── Forward to OpenCode server ─────────────────
  var options = {
    hostname: HOST,
    port: TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: {},
  };

  // Copy headers (skip host to avoid conflicts)
  var reqHeaders = req.headers || {};
  Object.keys(reqHeaders).forEach(function (key) {
    if (key !== "host") {
      options.headers[key] = reqHeaders[key];
    }
  });

  var proxyReq = http.request(options, function (proxyRes) {
    // Merge CORS headers into response
    var responseHeaders = {};
    var proxyHeaders = proxyRes.headers || {};
    Object.keys(proxyHeaders).forEach(function (key) {
      responseHeaders[key] = proxyHeaders[key];
    });
    // Override/add CORS headers
    Object.keys(CORS_HEADERS).forEach(function (key) {
      responseHeaders[key] = CORS_HEADERS[key];
    });

    res.writeHead(proxyRes.statusCode, responseHeaders);
    proxyRes.pipe(res);
  });

  proxyReq.on("error", function (err) {
    res.writeHead(502, { "Content-Type": "text/plain" });
    res.end("CORS Proxy Error: " + err.message);
  });

  req.pipe(proxyReq);
});

// ─── Start ──────────────────────────────────────────

server.listen(PROXY_PORT, HOST, function () {
  console.log(
    "[OpenCodeProxy] CORS proxy on http://" +
      HOST +
      ":" +
      PROXY_PORT +
      " → http://" +
      HOST +
      ":" +
      TARGET_PORT
  );
});
