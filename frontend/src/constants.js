// Environment constants
const {
    VITE_API_BASE_URL,
} = import.meta.env;

export const API_BASE_URL = VITE_API_BASE_URL || 'http://localhost:8000'; 