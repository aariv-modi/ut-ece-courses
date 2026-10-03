// @ts-check
import { defineConfig } from 'astro/config';

// Deployed to GitHub Pages under /<repo>/ — set SITE_BASE=/<repo> in CI; empty for local dev.
export default defineConfig({
  base: process.env.SITE_BASE || '/',
  trailingSlash: 'always',
});
