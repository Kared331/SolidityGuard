import axios from 'axios';

// API key is injected at build time via VITE_API_KEY env var
const apiKey = import.meta.env.VITE_API_KEY || '';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  headers: apiKey ? { 'X-API-Key': apiKey } : {},
});

export default client;
