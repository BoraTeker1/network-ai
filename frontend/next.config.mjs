/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          // CSP is deliberately deferred: Next.js inline scripts need nonces or
          // 'unsafe-inline', which deserves its own careful pass. Tracked in
          // PRODUCTION_CHECKLIST.md.
        ],
      },
    ];
  },
};

export default nextConfig;
