import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { getUserDateTime } from '../utils/datetime/get_current_time';
import { Event, EventCreate } from '../models/event';

const API_BASE_URL = 'http://localhost:8000';

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

interface TranscribeMessage {
  message: string;
}

interface User {
  id?: string;
  name: string;
}

interface LoginCredentials {
  email: string;
  password: string;
}

interface RegisterData {
  name: string;
  email: string;
  password: string;
}

interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  user_name: string;
  expires_in: number;
}

class CalendarAPI {
  private api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
  });

  private onAuthFailure?: () => void;

  constructor() {
    this.setupInterceptors();
  }

  setAuthFailureCallback(callback: () => void) {
    this.onAuthFailure = callback;
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        const token = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh
    this.api.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Only attempt refresh if:
        // 1. Status is 401 (Unauthorized)
        // 2. Request hasn't been retried yet
        // 3. This is not already a refresh request
        // 4. The error indicates token expiration (check WWW-Authenticate header)
        if (error.response?.status === 401 && 
            !originalRequest._retry && 
            !originalRequest.url?.includes('/auth/refresh')) {
              
          // Check if this is likely a token expiration error
          const isTokenExpired = this.isTokenExpiredError(error);
          if (isTokenExpired) {
            originalRequest._retry = true;

            try {
              const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
              if (refreshToken) {
                const response = await this.refreshToken(refreshToken);
                await this.storeTokens(response);
                
                // Retry the original request with new token
                originalRequest.headers.Authorization = `Bearer ${response.access_token}`;
                return this.api(originalRequest);
              }
            } catch (refreshError) {
              // Refresh failed, clear tokens and redirect to login
              await this.clearTokens();
              // Notify AuthContext that authentication failed
              if (this.onAuthFailure) {
                this.onAuthFailure();
              }
              throw refreshError;
            }
          }
        }

        return Promise.reject(error);
      }
    );
  }

  // Authentication methods
  async login(credentials: LoginCredentials): Promise<TokenResponse> {
    try {
      const response = await this.api.post('/auth/login', credentials);
      const tokenData = response.data;
      
      await this.storeTokens(tokenData);
      return tokenData;
    } catch (error) {
      throw error;
    }
  }

  async register(userData: RegisterData): Promise<TokenResponse> {
    try {
      const response = await this.api.post('/auth/register', userData);
      const tokenData = response.data;
      
      await this.storeTokens(tokenData);
      return tokenData;
    } catch (error) {
      throw error;
    }
  }

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    try {
      const response = await this.api.post('/auth/refresh', {
        refresh_token: refreshToken
      });
      return response.data;
    } catch (error) {
      console.error('Error refreshing token:', error);
      throw new Error('Token yenilenemedi');
    }
  }

  async logout(): Promise<void> {
    try {
      await this.api.post('/auth/logout');
    } catch (error) {
      console.error('Error logging out:', error);
    } finally {
      await this.clearTokens();
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = await this.api.get('/auth/me');
      return response.data;
    } catch (error) {
      console.error('Error getting current user:', error);
      throw new Error('Mevcut kullanıcı alınamadı');
    }
  }

  async changePassword(passwordRequest: PasswordChangeRequest): Promise<{message: string}> {
    try {
      const response = await this.api.patch('/auth/change-password', passwordRequest);
      return response.data;
    } catch (error) {
      console.error('Error changing password:', error);
      throw new Error('Şifre değiştirilemedi');
    }
  }

  // Token storage methods
  private async storeTokens(tokenData: TokenResponse): Promise<void> {
    await AsyncStorage.setItem(ACCESS_TOKEN_KEY, tokenData.access_token);
    await AsyncStorage.setItem(REFRESH_TOKEN_KEY, tokenData.refresh_token);
  }

  private async clearTokens(): Promise<void> {
    await AsyncStorage.removeItem(ACCESS_TOKEN_KEY);
    await AsyncStorage.removeItem(REFRESH_TOKEN_KEY);
  }

  async isAuthenticated(): Promise<boolean> {
    const token = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
    return !!token;
  }

  async getStoredTokens(): Promise<{ accessToken: string | null; refreshToken: string | null; }> {
    const accessToken = await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
    
    return { accessToken, refreshToken };
  }

  // Calendar methods
  async transcribeAudio(audioUri: string): Promise<TranscribeMessage> {
    try {
      // Create FormData for multipart upload
      const formData = new FormData();
      formData.append('audio', {
        uri: audioUri,
        type: 'audio/m4a', // Adjust based on your audio format
        name: 'audio.m4a'
      } as any);
    
      const response = await this.api.post('/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }); 

      return response.data;
      
    } catch (error) {
      console.error('Error transcribing audio:', error);
      throw new Error('Ses işlenemedi');
    }
  }

  async getEvents(date?: string): Promise<Event[]> {
    try {
      const params = date ? { date } : {};
      const response = await this.api.get('/events', { params });
      return response.data;
    } catch (error) {
      console.error('Error fetching events:', error);
      throw new Error('Etkinlikler alınamadı');
    }
  }

  async addEvent(event: EventCreate): Promise<Event> {
    try {
      const response = await this.api.post('/events', event);
      return response.data;
    } catch (error) {
      console.error('Error adding event:', error);
      throw error;
    }
  }

  async updateEvent(id: string, event: Partial<Event>): Promise<Event | null> {
    try {
      const response = await this.api.patch(`/events/${id}`, event);
      return response.data;
    } catch (error) {
      console.error('Error updating event:', error);
      throw error;
    }
  }

  async deleteEvent(eventId: string): Promise<{message: string}> {
    try {
      const response = await this.api.delete(`/events/${eventId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting event:', error);
      throw new Error('Etkinlik silinemedi');
    }
  }

  async deleteMultipleEvents(eventIds: string[]): Promise<{message: string}> {
    try {
      console.log(eventIds);
      const response = await this.api.delete('/events/bulk/', {
        params: { event_ids: eventIds },
        paramsSerializer: {
          indexes: null
        }
      });
      return response.data;
    } catch (error) {
      console.error('Error deleting multiple events:', error);
      throw new Error('Etkinlikler silinemedi');
    }
  }

  async processText(text: string): Promise<any> {
    try {
      const {currentDateTime: current_datetime, weekday, daysInMonth: days_in_month} = getUserDateTime()
      
      const response = await this.api.post('/assistant', { text, 
        current_datetime, 
        weekday, 
        days_in_month });
      return response.data;
    } catch (error) {
      console.error('Error processing text:', error);
      throw new Error('Metin işlenemedi');
    }
  }

  private isTokenExpiredError(error: any): boolean {
    // Check if this is an authentication error by looking for the WWW-Authenticate header
    // This is set by the backend for all token-related issues (expired, invalid, etc.)
    return error.response?.headers?.['www-authenticate']?.includes('Bearer');
  }
}

export const calendarAPI = new CalendarAPI();

// React Hook for using the API
export const useCalendarAPI = () => {
  return {
    // Authentication
    login: calendarAPI.login.bind(calendarAPI),
    register: calendarAPI.register.bind(calendarAPI),
    logout: calendarAPI.logout.bind(calendarAPI),
    refreshToken: calendarAPI.refreshToken.bind(calendarAPI),
    getCurrentUser: calendarAPI.getCurrentUser.bind(calendarAPI),
    changePassword: calendarAPI.changePassword.bind(calendarAPI),
    isAuthenticated: calendarAPI.isAuthenticated.bind(calendarAPI),
    getStoredTokens: calendarAPI.getStoredTokens.bind(calendarAPI),
    
    // Calendar
    transcribeAudio: calendarAPI.transcribeAudio.bind(calendarAPI),
    getEvents: calendarAPI.getEvents.bind(calendarAPI),
    addEvent: calendarAPI.addEvent.bind(calendarAPI),
    updateEvent: calendarAPI.updateEvent.bind(calendarAPI),
    deleteEvent: calendarAPI.deleteEvent.bind(calendarAPI),
    deleteMultipleEvents: calendarAPI.deleteMultipleEvents.bind(calendarAPI),
    processText: calendarAPI.processText.bind(calendarAPI),
  };
}; 