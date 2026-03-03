const BASE_URL = 'http://127.0.0.1:5000/api';

export const api = {
    getStats: async () => {
        const response = await fetch(`${BASE_URL}/stats`);
        if (!response.ok) throw new Error('Failed to fetch stats');
        return response.json();
    },

    uploadFile: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${BASE_URL}/upload`, {
            method: 'POST',
            body: formData,
        });
        
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Upload failed');
        return data;
    },

    search: async (query, limit = 5) => {
        const response = await fetch(`${BASE_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, limit })
        });
        
        if (!response.ok) throw new Error('Search failed');
        return response.json();
    }
};