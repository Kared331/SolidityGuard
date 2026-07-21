import axios from 'axios';

// API key is NOT included in frontend — it is injected by nginx proxy at runtime
// This prevents the API key from being exposed in the JavaScript bundle

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
});

export default client;
