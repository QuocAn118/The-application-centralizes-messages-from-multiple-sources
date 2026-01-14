import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, LoginRequest, LoginResponse } from '../types';
import apiClient from '../api/client';

interface AuthState {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    login: (credentials: LoginRequest) => Promise<void>;
    logout: () => void;
    setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            token: null,
            isAuthenticated: false,

            login: async (credentials: LoginRequest) => {
                try {
                    const response = await apiClient.post<LoginResponse>('/api/auth/login', credentials);
                    const { access_token } = response.data;

                    localStorage.setItem('access_token', access_token);

                    // Get user info
                    const userResponse = await apiClient.get<User>('/api/auth/me');
                    const user = userResponse.data;

                    set({
                        user,
                        token: access_token,
                        isAuthenticated: true,
                    });
                } catch (error) {
                    console.error('Login failed:', error);
                    throw error;
                }
            },

            logout: () => {
                localStorage.removeItem('access_token');
                set({
                    user: null,
                    token: null,
                    isAuthenticated: false,
                });
            },

            setUser: (user: User) => {
                set({ user });
            },
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                user: state.user,
                token: state.token,
                isAuthenticated: state.isAuthenticated,
            }),
        }
    )
);
