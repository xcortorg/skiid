const API_BASE_URL = '/api';

export async function fetchWithHeaders(endpoint: string, options = {}) {
  const defaultOptions = {
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'Content-Type': 'application/json'
    }
  };

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...(options as any).headers
    }
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchEconomyLogs(userId: string) {
  return fetchWithHeaders(`/logs/economy/${userId}`);
}

export async function fetchUserData(userId: string) {
  return fetchWithHeaders(`/user/${userId}`);
}

export async function fetchAllUserBlacklists() {
  return fetchWithHeaders('/blacklist/user/users');
}

export async function fetchAllCommandBlacklists() {
  return fetchWithHeaders('/blacklist/user/commands');
}

export async function fetchAllCogBlacklists() {
  return fetchWithHeaders('/blacklist/user/cogs');
}

export async function fetchAllServerBlacklists() {
  return fetchWithHeaders('/blacklist/server/servers');
}

export async function fetchAllServerCommandBlacklists() {
  return fetchWithHeaders('/blacklist/server/commands');
}

export async function fetchAllServerCogBlacklists() {
  return fetchWithHeaders('/blacklist/server/cogs');
}

export async function fetchTeamMembers() {
  try {
    const response = await fetch(`${API_BASE_URL}/team`);
    if (!response.ok) {
      throw new Error('Failed to fetch team members');
    }
    const data = await response.json();
    
    return data;
  } catch (error) {
    console.error('Error fetching team members:', error);
    throw error;
  }
}